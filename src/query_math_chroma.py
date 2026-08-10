import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "havruta_math_all")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")


def get_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)


def get_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(name=COLLECTION_NAME)


def query_high1_math(question: str, top_k: int = 3):
    model = get_embedding_model()
    collection = get_chroma_collection()

    query_text = f"query: {question}"

    query_embedding = model.encode([query_text], convert_to_numpy=True)

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k,
        where={"subject": "수학"},
    )

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    print("=" * 80)
    print("사용자 질문:", question)
    print("=" * 80)

    for i, doc_id in enumerate(ids):
        print()
        print(f"[검색 결과 {i + 1}]")
        print("ID:", doc_id)
        print("파일:", metadatas[i].get("file"))
        print("거리:", distances[i])
        print("-" * 80)
        print(documents[i])
        print("-" * 80)


if __name__ == "__main__":
    query_high1_math("기울기가 2이고 한 점을 지나는 직선의 방정식은 어떻게 구해?", top_k=3)
