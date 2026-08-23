from app.database.config import settings
from app.services.rag_service import search_chroma


def query_high1_math(question: str, top_k: int = 3) -> None:
    results = search_chroma(
        question,
        top_k,
        subject="수학",
        curriculum_year=settings.rag_curriculum_year,
    )

    print("=" * 80)
    print("사용자 질문:", question)
    print("교육과정:", settings.rag_curriculum_year)
    print("=" * 80)

    for index, result in enumerate(results, 1):
        print()
        print(f"[검색 결과 {index}]")
        print("ID:", result.source_id)
        print("파일:", result.metadata.get("file"))
        print("2022 정렬 방식:", result.metadata.get("curriculum_alignment"))
        print("관련도:", result.score)
        print("-" * 80)
        print(result.content)
        print("-" * 80)


if __name__ == "__main__":
    query_high1_math("기울기가 2이고 한 점을 지나는 직선의 방정식은 어떻게 구해?", top_k=3)
