from app.database.config import settings
from app.services.rag_service import search_chroma


SUBJECT_QUERIES = {
    "국어": "글의 중심 내용과 주제를 파악하는 방법",
    "영어": "자신의 의견을 영어로 표현하는 방법",
    "수학": "두 직선이 평행할 조건",
    "사회": "민주주의에서 시민 참여가 중요한 이유",
    "사회문화": "사회화와 사회 집단의 관계",
    "과학": "광합성 과정과 필요한 조건",
    "도덕": "도덕적 갈등 상황을 해결하는 방법",
    "기술가정": "지속 가능한 생활을 실천하는 방법",
    "정보": "알고리즘과 프로그램의 관계",
}


def evaluate() -> None:
    print(f"RAG 교육과정: {settings.rag_curriculum_year}")
    for subject, question in SUBJECT_QUERIES.items():
        results = search_chroma(
            question,
            1,
            subject=subject,
            curriculum_year=settings.rag_curriculum_year,
        )
        print("=" * 80)
        print(f"과목: {subject} / 질문: {question}")
        if not results:
            print("검색 결과 없음")
            continue
        result = results[0]
        print(
            f"ID: {result.source_id} / score={result.score:.4f} / "
            f"alignment={result.metadata.get('curriculum_alignment')}"
        )
        print("질문:", result.metadata.get("question"))
        print("정답:", result.metadata.get("answer"))


if __name__ == "__main__":
    evaluate()
