from app.database.connection import SessionLocal
from app.services.rag_service import index_local_documents, search
from app.services.tutor_service import tutor_reply


def search_math_context(question: str, top_k: int = 3) -> list[dict]:
    db = SessionLocal()
    try:
        index_local_documents(db)
        return [
            {
                "id": result.source_id,
                "document": result.content,
                "metadata": result.metadata,
                "distance": round(1 - result.score, 4),
                "lexical_score": result.score,
            }
            for result in search(db, question, top_k)
        ]
    finally:
        db.close()


def run_local_rag_tutor(question: str) -> None:
    db = SessionLocal()
    try:
        index_local_documents(db)
        answer, feedback, contexts = tutor_reply(db, "고1 직선의 방정식", question)
        print("=" * 80)
        print(answer)
        print(f"\n평가 점수: {feedback['score']}")
        print("\n검색 근거")
        for index, context in enumerate(contexts, 1):
            print(f"{index}. {context.source_id} / 관련도 {context.score:.4f}")
    finally:
        db.close()


if __name__ == "__main__":
    print("고1 수학 로컬 RAG 튜터입니다. 종료하려면 q를 입력하세요.")
    while True:
        user_question = input("질문을 입력하세요: ").strip()
        if user_question.lower() in {"q", "quit", "exit"}:
            break
        if user_question:
            run_local_rag_tutor(user_question)
