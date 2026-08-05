from app.services.rag_retriever import search

TEST_QUERIES = [
    "기울기가 2이고 점 (1,-2)를 지나는 직선의 방정식은?",
    "평행한 직선의 기울기는 어떻게 돼?",
    "x절편과 y절편은 어떻게 구해?",
    "두 점의 x좌표가 같으면 직선은 어떻게 돼?",
    "점 (0,-2)를 지나고 기울기가 3인 직선의 방정식은?",
    "중학교 1학년 수학에서 일차방정식은 어떻게 설명돼?",
    "고등학교 1학년 수학에서 직선의 방정식을 설명해줘",
]


def print_result(question: str, results: list) -> None:
    print(f"\n=== 질의: {question} ===")
    if not results:
        print("검색 결과가 없습니다.")
        return

    for rank, item in enumerate(results, start=1):
        metadata = item.get("metadata", {})
        print(f"[랭크 {rank}] id={item.get('id')}")
        print(f"  distance={item.get('distance')}")
        print(f"  lexical_score={item.get('lexical_score')}")
        print(f"  file={metadata.get('file', '')}")
        print(f"  source_path={metadata.get('source_path', '')}")
        doc_preview = item.get("document", "")[:240].replace("\n", " ")
        print(f"  document={doc_preview}...")


if __name__ == "__main__":
    for query in TEST_QUERIES:
        results = search(query, top_k=3)
        print_result(query, results)
