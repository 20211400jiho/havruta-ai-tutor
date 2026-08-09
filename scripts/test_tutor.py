import traceback
from app.services.rag_tutor import generate_tutor_answer
from app.services.rag_retriever import search


def run_test(question, school_level, grade, subject, top_k=3):
    print("\n--- 테스트 시작 ---")
    print(f"질문: {question}")
    print(f"필터: school_level={school_level} / grade={grade} / subject={subject}")
    try:
        result = generate_tutor_answer(
            question,
            school_level=school_level,
            grade=grade,
            subject=subject,
            top_k=top_k,
        )
    except Exception as exc:
        print("generate_tutor_answer 실행 중 오류:")
        traceback.print_exc()
        return

    answer = result.get("answer", "")
    mode = result.get("mode", "")
    contexts = result.get("contexts", []) or []
    retrieved = result.get("retrieved_contexts", []) or []

    print(f"mode: {mode}")
    print("answer:\n")
    print(answer)
    print()
    print(f"contexts 개수 (실제 사용된 문서): {len(contexts)}")
    print(f"retrieved_contexts 개수 (검색된 문서): {len(retrieved)}")

    if len(retrieved) > 0:
        # 검색에서 반환된 메타 정보를 확인하려면 동일 파라미터로 상세 검색 수행
        try:
            hits = search(question, top_k=top_k, school_level=school_level, grade=grade, subject=subject)
            if hits:
                first = hits[0]
                metadata = first.get("metadata", {})
                print("첫 번째 검색된 문서 메타:")
                print(f"  file: {metadata.get('file', '')}")
                print(f"  source_path: {metadata.get('source_path', '')}")
                print(f"  distance: {first.get('distance')}")
            else:
                print("검색 결과는 있으나 상세 hits를 가져오지 못했습니다.")
        except Exception:
            print("검색 상세 정보 조회 중 오류:")
            traceback.print_exc()


def main():
    tests = [
        # 1. 데이터셋에 있는 질문
        ("일차방정식은 어떻게 풀어?", "중학교", "1학년", "수학"),
        # 2. 데이터셋에 있는 질문
        ("전류는 무엇이야?", "중학교", "2학년", "과학"),
        # 3. 데이터셋에 있는 질문
        ("연구 윤리는 왜 중요해?", "고등학교", "1학년", "과학"),
        # 4. 데이터셋에 없는 질문
        ("함수의 극한은 무엇이야?", "고등학교", "2학년", "수학"),
        # 5. 데이터셋에 없는 질문
        ("조건부확률은 무엇이야?", "고등학교", "3학년", "수학"),
        # 6. 과목 필터 테스트 (subject=국어)
        ("전류는 무엇이야?", "중학교", "2학년", "국어"),
    ]

    for q, sl, g, s in tests:
        run_test(question=q, school_level=sl, grade=g, subject=s, top_k=3)


if __name__ == "__main__":
    main()
