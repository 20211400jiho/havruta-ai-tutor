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
STOPWORDS = {"그리고", "그러므로", "어떻게", "무엇", "인가요", "입니다", "있는", "대한", "직선", "문제"}
logger = logging.getLogger(__name__)
_chroma_lock = Lock()


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


def load_math_rows() -> list[dict]:
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
                "content": content,
            }
        )
    return rows


def index_local_documents(db: Session) -> int:
    indexed = 0
    for row in load_math_rows():
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
        }
        if chunk is None:
            db.add(DocumentChunk(document_id=document.id, chunk_index=0, content=row["content"], metadata_json=metadata))
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
) -> list[SearchResult]:
    query_tokens = tokenize(query)
    results: list[SearchResult] = []
    chunks = db.query(DocumentChunk).join(Document)
    if subject:
        chunks = chunks.filter(Document.subject == subject)
    for chunk in chunks.all():
        document_tokens = tokenize(chunk.content)
        overlap = query_tokens & document_tokens
        exact_bonus = sum(2 for token in query_tokens if token in chunk.content.lower())
        raw_score = len(overlap) * 3 + exact_bonus
        if raw_score == 0:
            continue
        score = min(1.0, raw_score / max(6, len(query_tokens) * 4))
        metadata = dict(chunk.metadata_json or {})
        metadata.setdefault("subject", chunk.document.subject)
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
def _chroma_resources():
    try:
        import chromadb
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Chroma RAG 패키지가 설치되지 않았습니다.") from exc

    chroma_dir = Path(settings.chroma_dir).expanduser()
    if not chroma_dir.is_absolute():
        chroma_dir = BASE_DIR / chroma_dir
    if not (chroma_dir / "chroma.sqlite3").is_file():
        raise RuntimeError(f"ChromaDB를 찾을 수 없습니다: {chroma_dir}")

    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_collection(name=settings.chroma_collection)
    model_source = settings.embedding_model
    if settings.embedding_local_files_only and not Path(model_source).expanduser().exists():
        model_source = snapshot_download(model_source, local_files_only=True)
    model = SentenceTransformer(
        model_source,
        local_files_only=settings.embedding_local_files_only,
    )
    return collection, model


def _chroma_search(query: str, top_k: int, subject: str | None = None) -> list[SearchResult]:
    collection, model = _chroma_resources()
    with _chroma_lock:
        query_embedding = model.encode([f"query: {query}"], convert_to_numpy=True)
        query_options = {
            "query_embeddings": query_embedding.tolist(),
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if subject:
            query_options["where"] = {"subject": subject}
        response = collection.query(
            **query_options,
        )

    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]
    results: list[SearchResult] = []
    for source_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
        distance_value = float(distance)
        result_metadata = dict(metadata or {})
        result_metadata["retriever"] = "chroma"
        results.append(
            SearchResult(
                chunk_id=None,
                source_id=str(source_id),
                content=content or "",
                score=round(max(0.0, min(1.0, 1.0 - distance_value)), 4),
                metadata=result_metadata,
            )
        )
    return results


def search(
    db: Session,
    query: str,
    top_k: int = 3,
    subject: str | None = None,
) -> list[SearchResult]:
    normalized_subject = subject.strip() if subject else None
    provider = settings.rag_provider.strip().lower()
    if provider in {"auto", "chroma"}:
        try:
            results = _chroma_search(query, top_k, normalized_subject)
            if results:
                return results
        except Exception as exc:
            logger.warning("Chroma 검색에 실패해 MySQL 어휘 검색으로 대체합니다: %s", exc)
    return _lexical_search(db, query, top_k, normalized_subject)
