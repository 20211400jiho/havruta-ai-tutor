from app.database.connection import SessionLocal
from app.services.rag_service import index_local_documents, search


TEST_QUESTIONS = [
    "기울기가 2이고 점 (1,-2)를 지나는 직선의 방정식은?",
    "평행한 직선의 기울기는 어떻게 돼?",
    "x절편과 y절편은 어떻게 구해?",
    "두 점의 x좌표가 같으면 직선은 어떻게 돼?",
]


def evaluate() -> None:
    db = SessionLocal()
    try:
        index_local_documents(db)
        for question in TEST_QUESTIONS:
            print("=" * 80, f"\n질문: {question}")
            for rank, result in enumerate(search(db, question, 3), 1):
                print(f"{rank}위: {result.source_id} / score={result.score:.4f}")
    finally:
        db.close()


if __name__ == "__main__":
    evaluate()
