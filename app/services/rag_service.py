import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
TOKEN_PATTERN = re.compile(r"\(-?\d+(?:/\d+)?\s*,\s*-?\d+(?:/\d+)?\)|-?\d+(?:/\d+)?|[가-힣A-Za-z]+")
STOPWORDS = {"그리고", "그러므로", "어떻게", "무엇", "인가요", "입니다", "있는", "대한", "직선", "문제"}


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


def search(db: Session, query: str, top_k: int = 3) -> list[SearchResult]:
    query_tokens = tokenize(query)
    results: list[SearchResult] = []
    for chunk in db.query(DocumentChunk).all():
        document_tokens = tokenize(chunk.content)
        overlap = query_tokens & document_tokens
        exact_bonus = sum(2 for token in query_tokens if token in chunk.content.lower())
        raw_score = len(overlap) * 3 + exact_bonus
        if raw_score == 0:
            continue
        score = min(1.0, raw_score / max(6, len(query_tokens) * 4))
        metadata = chunk.metadata_json or {}
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
