from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from load_math_json import load_high1_math


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"


def build_text_for_embedding(row) -> str:
    return f"""
설명: {row["description"]}
질문: {row["question"]}
정답: {row["answer"]}
성취기준2015: {row["achievement_2015"]}
성취기준2022: {row["achievement_2022"]}
""".strip()


def get_embedding_model():
    return SentenceTransformer("intfloat/multilingual-e5-base")


def get_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    collection = client.get_or_create_collection(
        name="high1_math"
    )

    return collection


def index_high1_math():
    df = load_high1_math()

    print("로드된 데이터 개수:", len(df))

    if df.empty:
        raise ValueError("로드된 데이터가 없습니다.")

    model = get_embedding_model()
    collection = get_chroma_collection()

    ids = []
    documents = []
    metadatas = []

    for _, row in df.iterrows():
        doc_text = build_text_for_embedding(row)

        ids.append(row["id"])
        documents.append(doc_text)
        metadatas.append({
            "file": row["file"],
            "subject": row["subject"],
            "grade": row["grade"],
        })

    print("임베딩 생성 중...")
    embeddings = model.encode(documents, convert_to_numpy=True)

    print("ChromaDB 저장 중...")

    collection.upsert(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadatas,
    )

    print("인덱싱 완료")
    print("저장된 문서 수:", collection.count())


if __name__ == "__main__":
    index_high1_math()