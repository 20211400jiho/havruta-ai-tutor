import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "havruta_math_all"
DB_DIR = Path(__file__).resolve().parents[2] / "app" / "database" / "chroma_db"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
KEYWORDS = [
    "기울기",
    "직선",
    "방정식",
    "평행",
    "절편",
    "x절편",
    "y절편",
    "x좌표",
    "y좌표",
    "함수",
    "그래프",
    "수학",
    "국어",
    "영어",
    "과학",
    "사회",
]

NUMERIC_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
FRACTION_PATTERN = re.compile(r"-?\d+/\d+")
COORD_PATTERN = re.compile(r"\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\)")


def get_chroma_client() -> chromadb.api.client.Client:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(DB_DIR))


def get_collection(client: chromadb.api.client.Client) -> chromadb.api.models.Collection:
    existing = [collection.name for collection in client.list_collections()]
    if COLLECTION_NAME not in existing:
        raise RuntimeError(f"컬렉션이 존재하지 않습니다: {COLLECTION_NAME}")
    return client.get_collection(name=COLLECTION_NAME)


def build_query_text(question: str) -> str:
    return f"query: {question}"


def extract_query_tokens(question: str) -> List[Dict[str, object]]:
    tokens = []
    lower_text = question.strip().lower()
    for coord in COORD_PATTERN.findall(question):
        tokens.append({"token": coord, "weight": 3})

    for fraction in set(FRACTION_PATTERN.findall(question)):
        tokens.append({"token": fraction, "weight": 3})

    for numeric in set(NUMERIC_PATTERN.findall(question)):
        if "/" not in numeric:
            tokens.append({"token": numeric, "weight": 3})

    for keyword in KEYWORDS:
        if keyword in lower_text:
            tokens.append({"token": keyword, "weight": 1})

    return tokens


def calculate_lexical_score(document: str, tokens: List[Dict[str, object]]) -> int:
    score = 0
    doc_lower = document.lower()
    for item in tokens:
        token = str(item["token"]).lower()
        if token and token in doc_lower:
            score += int(item["weight"])
    return score


def search(
    question: str,
    top_k: int = 3,
    school_level: Optional[str] = None,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
) -> List[Dict[str, object]]:
    client = get_chroma_client()
    collection = get_collection(client)
    total_count = collection.count()
    if total_count == 0:
        return []

    where_filters: List[Dict[str, str]] = []
    if school_level:
        where_filters.append({"school_level": school_level})
    if grade:
        where_filters.append({"grade": grade})
    if subject:
        where_filters.append({"subject": subject})

    where_clause = None
    if where_filters:
        where_clause = where_filters[0] if len(where_filters) == 1 else {"$and": where_filters}

    candidate_k = min(20, total_count)
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_text = build_query_text(question)
    query_embedding = model.encode([query_text], batch_size=1, show_progress_bar=False, convert_to_numpy=True)

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=candidate_k,
        include=["documents", "metadatas", "distances"],
        where=where_clause,
    )

    query_tokens = extract_query_tokens(question)
    hits: List[Dict[str, object]] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    for idx, doc_text in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else 0.0
        doc_str = str(doc_text)
        lexical_score = calculate_lexical_score(doc_str, query_tokens)
        hits.append(
            {
                "id": ids[idx] if idx < len(ids) else "",
                "document": doc_str,
                "metadata": metadata,
                "distance": float(distance),
                "lexical_score": lexical_score,
            }
        )

    hits.sort(key=lambda item: (-item["lexical_score"], item["distance"]))
    return hits[:top_k]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Training RAG 검색기")
    parser.add_argument("question", type=str, help="검색할 질문 텍스트")
    parser.add_argument("--school-level", type=str, default=None, help="검색할 학교급")
    parser.add_argument("--grade", type=str, default=None, help="검색할 학년")
    parser.add_argument("--subject", type=str, default=None, help="검색할 과목")
    parser.add_argument("--top-k", type=int, default=3, help="출력할 결과 수")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = search(
        args.question,
        top_k=args.top_k,
        school_level=args.school_level,
        grade=args.grade,
        subject=args.subject,
    )
    if not results:
        print("조건에 맞는 검색 결과가 없습니다.")
        return

    for index, item in enumerate(results, start=1):
        metadata = item.get("metadata", {})
        print(f"=== 결과 {index} ===")
        print(f"id: {item.get('id')}")
        print(f"distance: {item.get('distance')}")
        print(f"lexical_score: {item.get('lexical_score')}")
        print(f"file: {metadata.get('file', '')}")
        print(f"source_path: {metadata.get('source_path', '')}")
        print(f"document:\n{item.get('document', '')[:500]}\n")


if __name__ == "__main__":
    main()
