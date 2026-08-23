import chromadb
from sentence_transformers import SentenceTransformer

from app.database.config import settings
from src.load_math_json import load_high1_math


def build_text_for_embedding(row) -> str:
    return f"""
설명: {row["description"]}
질문: {row["question"]}
정답: {row["answer"]}
성취기준2015: {row["achievement_2015"]}
성취기준2022: {row["achievement_2022"]}
""".strip()


def get_embedding_model():
    return SentenceTransformer(settings.embedding_model)


def get_chroma_collection():
    client = chromadb.PersistentClient(path=settings.chroma_dir)

    collection = client.get_or_create_collection(
        name=settings.chroma_collection
    )

    return collection


def index_high1_math():
    rows = load_high1_math()

    print("로드된 데이터 개수:", len(rows))

    if not rows:
        raise ValueError("로드된 데이터가 없습니다.")

    model = get_embedding_model()
    collection = get_chroma_collection()

    ids = []
    documents = []
    metadatas = []

    for row in rows:
        doc_text = build_text_for_embedding(row)

        ids.append(row["id"])
        documents.append(f"passage: {doc_text}")
        metadatas.append({
            "file": row["file"],
            "subject": row["subject"],
            "grade": row["grade"],
            "question": row["question"],
            "answer": row["answer"],
            "description": row["description"],
            "curriculum_year": row["curriculum_year"],
            "achievement_standard_2022": row["achievement_2022"],
            "aligned_2022": bool(row["achievement_2022"]) or row["curriculum_year"] == "2022",
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
