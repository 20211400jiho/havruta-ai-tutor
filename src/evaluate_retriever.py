from local_rag_tutor import search_math_context


TEST_QUESTIONS = [
    "기울기가 2이고 점 (1,-2)를 지나는 직선의 방정식은?",
    "기울기가 -4이고 점 (1,-2)를 지나는 직선의 방정식은?",
    "기울기가 1/2이고 점 (2,3)을 지나는 직선의 방정식은?",
    "평행한 직선의 기울기는 어떻게 돼?",
    "x절편과 y절편은 어떻게 구해?",
    "두 점의 x좌표가 같으면 직선은 어떻게 돼?",
    "점 (0,-2)를 지나고 기울기가 3인 직선의 방정식은?",
]


def evaluate():
    for question in TEST_QUESTIONS:
        print("=" * 100)
        print("질문:", question)

        contexts = search_math_context(question, top_k=3)

        for i, ctx in enumerate(contexts, start=1):
            print()
            print(f"[{i}위]")
            print("ID:", ctx["id"])
            print("거리:", round(ctx["distance"], 4))
            print("Lexical score:", ctx["lexical_score"])
            print("파일:", ctx["metadata"].get("file"))

            document = ctx["document"]
            short_doc = document.replace("\n", " ")[:180]
            print("내용:", short_doc, "...")


if __name__ == "__main__":
    evaluate()
