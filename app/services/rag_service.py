import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

from sqlalchemy.orm import Session

from app.database.config import settings
from app.models.document import Document, DocumentChunk


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
TOKEN_PATTERN = re.compile(r"\(-?\d+(?:/\d+)?\s*,\s*-?\d+(?:/\d+)?\)|-?\d+(?:/\d+)?|[가-힣A-Za-z]+")
SELECTED_STANDARD_PATTERN = re.compile(r"\[((?:9|10|12)[^\]\s]+)]")
STOPWORDS = {"그리고", "그러므로", "어떻게", "무엇", "인가요", "입니다", "있는", "대한", "직선", "문제"}
logger = logging.getLogger(__name__)
_chroma_lock = Lock()
STRUCTURED_CONTENT_FIELDS = {
    "과목": "subject",
    "학년": "grade",
    "설명": "description",
    "질문": "question",
    "정답": "answer",
    "성취기준2022": "achievement_standard_2022",
    "2022 성취기준": "achievement_standard_2022",
}


@dataclass
class SearchResult:
    chunk_id: int | None
    source_id: str
    content: str
    score: float
    metadata: dict


def _list_value(source: dict, *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value:
            return " ".join(value) if isinstance(value, list) else str(value)
    return ""


def load_local_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        raw = data.get("raw_data_info", {})
        source = data.get("source_data_info", {})
        learning = data.get("learning_data_info", {})
        source_id = learning.get("learning_data_name") or source.get("source_data_name") or path.stem
        description = learning.get("text_description", "")
        question = learning.get("text_qa", "")
        answer = learning.get("text_an", "")
        achievement_2015 = _list_value(source, "2015_achievement_standard", "achievement_2015")
        achievement_2022 = _list_value(source, "2022_achievement_standard", "achievement_2022")
        content = "\n".join(
            value
            for value in [
                f"설명: {description}" if description else "",
                f"질문: {question}" if question else "",
                f"정답: {answer}" if answer else "",
                f"2015 성취기준: {achievement_2015}" if achievement_2015 else "",
                f"2022 성취기준: {achievement_2022}" if achievement_2022 else "",
            ]
            if value
        )
        rows.append(
            {
                "id": source_id,
                "file": path.name,
                "subject": raw.get("subject_name") or raw.get("subject") or "수학",
                "grade": raw.get("grade_name") or raw.get("grade") or "1학년",
                "description": description,
                "question": question,
                "answer": answer,
                "curriculum_year": str(raw.get("revision_year") or raw.get("curriculum_year") or ""),
                "achievement_2015": achievement_2015,
                "achievement_2022": achievement_2022,
                "content": content,
            }
        )
    return rows


def index_local_documents(db: Session) -> int:
    indexed = 0
    for row in load_local_rows():
        document = db.query(Document).filter(Document.file_path == row["file"]).first()
        if document is None:
            document = Document(
                title=row["id"],
                subject=row["subject"],
                grade=row["grade"],
                source_type="textbook",
                file_path=row["file"],
            )
            db.add(document)
            db.flush()
        else:
            document.title = row["id"]
            document.subject = row["subject"]
            document.grade = row["grade"]
        chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id, DocumentChunk.chunk_index == 0)
            .first()
        )
        metadata = {
            "source_id": row["id"],
            "file": row["file"],
            "question": row["question"],
            "answer": row["answer"],
            "description": row["description"],
            "subject": row["subject"],
            "grade": row["grade"],
            "curriculum_year": row["curriculum_year"],
            "achievement_standard_2022": row["achievement_2022"],
        }
        if chunk is None:
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=0,
                    content=row["content"],
                    metadata_json=metadata,
                )
            )
            indexed += 1
        else:
            chunk.content = row["content"]
            chunk.metadata_json = metadata
    db.commit()
    return indexed


def tokenize(text: str) -> set[str]:
    return {
        token.lower().replace(" ", "")
        for token in TOKEN_PATTERN.findall(text)
        if len(token) > 1 and token not in STOPWORDS
    }


def _lexical_search(
    db: Session,
    query: str,
    top_k: int = 3,
    subject: str | None = None,
    curriculum_year: str | None = None,
    standard_code: str | None = None,
    unit_code: str | None = None,
) -> list[SearchResult]:
    query_tokens = tokenize(query)
    results: list[SearchResult] = []
    chunks = db.query(DocumentChunk).join(Document)
    if subject:
        chunks = chunks.filter(Document.subject == subject)
    for chunk in chunks.all():
        metadata = _metadata_from_content(chunk.metadata_json, chunk.content)
        metadata.setdefault("subject", chunk.document.subject)
        if not _is_curriculum_aligned(metadata, curriculum_year):
            continue
        if standard_code and f"[{standard_code}]" not in str(
            metadata.get("achievement_standard_2022") or chunk.content
        ):
            continue
        if unit_code and f"[{unit_code}-" not in str(
            metadata.get("achievement_standard_2022") or chunk.content
        ):
            continue
        document_tokens = tokenize(chunk.content)
        overlap = query_tokens & document_tokens
        exact_bonus = sum(2 for token in query_tokens if token in chunk.content.lower())
        raw_score = len(overlap) * 3 + exact_bonus
        if raw_score == 0:
            continue
        score = min(1.0, raw_score / max(6, len(query_tokens) * 4))
        metadata["rag_curriculum_year"] = curriculum_year
        metadata["curriculum_alignment"] = _curriculum_alignment(metadata, curriculum_year)
        metadata["selected_standard_code"] = standard_code
        metadata["selected_unit_code"] = unit_code
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                source_id=metadata.get("source_id", str(chunk.id)),
                content=chunk.content,
                score=round(score, 4),
                metadata=metadata,
            )
        )
    results.sort(key=lambda result: result.score, reverse=True)
    return results[:top_k]


@lru_cache(maxsize=1)
def _chroma_collection():
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("Chroma RAG 패키지가 설치되지 않았습니다.") from exc

    chroma_dir = Path(settings.chroma_dir).expanduser()
    if not chroma_dir.is_absolute():
        chroma_dir = BASE_DIR / chroma_dir
    if not (chroma_dir / "chroma.sqlite3").is_file():
        raise RuntimeError(f"ChromaDB를 찾을 수 없습니다: {chroma_dir}")

    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_collection(name=settings.chroma_collection)


@lru_cache(maxsize=1)
def _embedding_model():
    try:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("임베딩 패키지가 설치되지 않았습니다.") from exc

    model_source = settings.embedding_model
    if settings.embedding_local_files_only and not Path(model_source).expanduser().exists():
        model_source = snapshot_download(model_source, local_files_only=True)
    return SentenceTransformer(
        model_source,
        local_files_only=settings.embedding_local_files_only,
    )


def _metadata_from_content(metadata: dict | None, content: str) -> dict:
    """보관된 Chroma 문서 본문에서 빠진 구조화 필드를 복구한다."""
    result = dict(metadata or {})
    for line in content.splitlines():
        label, separator, value = line.partition(":")
        field = STRUCTURED_CONTENT_FIELDS.get(label.strip())
        if separator and field and value.strip() and not result.get(field):
            result[field] = value.strip()
    return result


def _curriculum_alignment(metadata: dict, curriculum_year: str | None) -> str | None:
    if not curriculum_year:
        return None
    if str(metadata.get("curriculum_year") or "").strip() == curriculum_year:
        return "source"
    if str(metadata.get(f"achievement_standard_{curriculum_year}") or "").strip():
        return "achievement_standard"
    return None


def _is_curriculum_aligned(metadata: dict, curriculum_year: str | None) -> bool:
    return curriculum_year is None or _curriculum_alignment(metadata, curriculum_year) is not None


def _chroma_where(subject: str | None, curriculum_year: str | None = None) -> dict | None:
    clauses: list[dict] = []
    if subject:
        clauses.append({"subject": {"$eq": subject}})
    if curriculum_year:
        clauses.append({"curriculum_year": {"$eq": curriculum_year}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _query_chroma(
    collection,
    query_embedding: list,
    result_count: int,
    where: dict | None,
    standard_code: str | None = None,
    unit_code: str | None = None,
) -> dict:
    query_options = {
        "query_embeddings": query_embedding,
        "n_results": result_count,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_options["where"] = where
    if standard_code:
        query_options["where_document"] = {"$contains": f"[{standard_code}]"}
    elif unit_code:
        query_options["where_document"] = {"$contains": f"[{unit_code}-"}
    return collection.query(**query_options)


def search_chroma(
    query: str,
    top_k: int,
    subject: str | None = None,
    curriculum_year: str | None = None,
    standard_code: str | None = None,
    unit_code: str | None = None,
) -> list[SearchResult]:
    collection = _chroma_collection()
    model = _embedding_model()
    collection_count = collection.count()
    if collection_count == 0:
        return []
    with _chroma_lock:
        query_embedding = model.encode([f"query: {query}"], convert_to_numpy=True)
        query_vector = query_embedding.tolist()

    results: list[SearchResult] = []
    seen_ids: set[str] = set()

    def append_response(response: dict) -> None:
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        for source_id, content, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=False,
        ):
            normalized_id = str(source_id)
            if normalized_id in seen_ids:
                continue
            result_metadata = _metadata_from_content(metadata, content or "")
            if not _is_curriculum_aligned(result_metadata, curriculum_year):
                continue
            if standard_code and f"[{standard_code}]" not in str(
                result_metadata.get("achievement_standard_2022") or ""
            ):
                continue
            if unit_code and f"[{unit_code}-" not in str(
                result_metadata.get("achievement_standard_2022") or ""
            ):
                continue
            seen_ids.add(normalized_id)
            distance_value = float(distance)
            result_metadata["retriever"] = "chroma"
            result_metadata["rag_curriculum_year"] = curriculum_year
            result_metadata["curriculum_alignment"] = _curriculum_alignment(
                result_metadata,
                curriculum_year,
            )
            result_metadata["selected_standard_code"] = standard_code
            result_metadata["selected_unit_code"] = unit_code
            results.append(
                SearchResult(
                    chunk_id=None,
                    source_id=normalized_id,
                    content=content or "",
                    score=round(max(0.0, min(1.0, 1.0 - distance_value)), 4),
                    metadata=result_metadata,
                )
            )
            if len(results) == top_k:
                return

    if subject and curriculum_year:
        with _chroma_lock:
            direct_response = _query_chroma(
                collection,
                query_vector,
                min(max(top_k * 2, 10), collection_count),
                _chroma_where(subject, curriculum_year),
                standard_code,
                unit_code,
            )
        append_response(direct_response)
        if len(results) == top_k:
            return results

    with _chroma_lock:
        mapped_response = _query_chroma(
            collection,
            query_vector,
            min(max(top_k * 8, 50), collection_count),
            _chroma_where(subject),
            standard_code,
            unit_code,
        )
    append_response(mapped_response)
    return results[:top_k]


def has_subject_documents(
    db: Session,
    subject: str,
    curriculum_year: str | None = None,
) -> bool:
    normalized_subject = subject.strip()
    if not normalized_subject:
        return False
    chunks = db.query(DocumentChunk).join(Document).filter(Document.subject == normalized_subject)
    for chunk in chunks.all():
        metadata = dict(chunk.metadata_json or {})
        if _is_curriculum_aligned(metadata, curriculum_year):
            return True
    if settings.rag_provider.strip().lower() not in {"auto", "chroma"}:
        return False
    try:
        collection = _chroma_collection()
        if curriculum_year:
            direct = collection.get(
                where=_chroma_where(normalized_subject, curriculum_year),
                limit=1,
                include=["metadatas"],
            )
            if direct.get("ids"):
                return True
        mapped = collection.get(
            where=_chroma_where(normalized_subject),
            limit=100,
            include=["documents", "metadatas"],
        )
        return any(
            _is_curriculum_aligned(_metadata_from_content(metadata, content or ""), curriculum_year)
            for content, metadata in zip(
                mapped.get("documents") or [],
                mapped.get("metadatas") or [],
                strict=False,
            )
        )
    except Exception as exc:
        logger.warning("Chroma 과목 상태 확인에 실패했습니다: %s", exc)
        return False


def search(
    db: Session,
    query: str,
    top_k: int = 3,
    subject: str | None = None,
    curriculum_year: str | None = None,
    unit_code: str | None = None,
) -> list[SearchResult]:
    normalized_subject = subject.strip() if subject else None
    normalized_curriculum_year = (
        settings.rag_curriculum_year if curriculum_year is None else curriculum_year
    ).strip() or None
    selected_standard_match = SELECTED_STANDARD_PATTERN.search(query)
    selected_standard_code = selected_standard_match.group(1) if selected_standard_match else None
    normalized_unit_code = unit_code.strip() if unit_code else None
    provider = settings.rag_provider.strip().lower()
    if provider in {"auto", "chroma"}:
        try:
            results = search_chroma(
                query,
                top_k,
                normalized_subject,
                normalized_curriculum_year,
                selected_standard_code,
                normalized_unit_code,
            )
            if results:
                return results
        except Exception as exc:
            logger.warning("Chroma 검색에 실패해 MySQL 어휘 검색으로 대체합니다: %s", exc)
    return _lexical_search(
        db,
        query,
        top_k,
        normalized_subject,
        normalized_curriculum_year,
        selected_standard_code,
        normalized_unit_code,
    )
