from pathlib import Path
import re

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"

IMPORTANT_KEYWORDS = (
    "기울기",
    "직선",
    "방정식",
    "평행",
    "x절편",
    "y절편",
    "절편",
    "x좌표",
    "y좌표",
)


def extract_important_terms(text: str) -> list[str]:
    """텍스트에서 숫자와 검색에 중요한 수학 키워드를 추출한다."""
    coordinate_terms = [
        f"({x},{y})"
        for x, y in re.findall(
            r"\(\s*(-?\d+(?:/\d+)?)\s*,\s*(-?\d+(?:/\d+)?)\s*\)",
            text,
        )
    ]
    number_terms = re.findall(r"(?<![\d.])-?\d+(?:/\d+)?(?![\d.])", text)
    keyword_terms = [keyword for keyword in IMPORTANT_KEYWORDS if keyword in text]

    # 같은 숫자나 키워드가 반복되어도 한 번만 점수를 부여한다.
    return list(dict.fromkeys(coordinate_terms + number_terms + keyword_terms))


def lexical_score(question: str, document: str) -> int:
    """질문의 중요 term이 문서에 정확히 등장하는 정도를 점수화한다."""
    question_terms = extract_important_terms(question)
    document_terms = set(extract_important_terms(document))

    return sum(
        3 if re.fullmatch(r"(?:-?\d+(?:/\d+)?|\(-?\d+(?:/\d+)?,-?\d+(?:/\d+)?\))", term) else 1
        for term in question_terms
        if term in document_terms
    )


def get_embedding_model():
    return SentenceTransformer("intfloat/multilingual-e5-base")


def get_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(name="high1_math")
    return collection


def search_math_context(question: str, top_k: int = 3):
    model = get_embedding_model()
    collection = get_chroma_collection()

    query_text = f"query: {question}"
    query_embedding = model.encode([query_text], convert_to_numpy=True)

    candidate_k = min(10, collection.count())
    if candidate_k == 0:
        return []

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=candidate_k,
    )

    contexts = []

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i in range(len(ids)):
        contexts.append({
            "id": ids[i],
            "document": documents[i],
            "metadata": metadatas[i],
            "distance": distances[i],
            "lexical_score": lexical_score(question, documents[i]),
        })

    contexts.sort(key=lambda x: (-x["lexical_score"], x["distance"]))
    return contexts[:top_k]


def make_local_tutor_answer(question: str, contexts: list[dict]) -> str:
    if not contexts:
        return "관련된 수학 자료를 찾지 못했어요. 질문을 조금 더 구체적으로 바꿔볼까요?"

    best = contexts[0]
    document = best["document"]

    answer = f"""
질문: {question}

가장 관련 있는 학습 자료를 찾았어요.

{document}

이 내용을 바탕으로 정리하면,
문제에서 주어진 조건을 먼저 확인한 뒤, 그 조건에 맞는 공식을 적용하면 됩니다.

예를 들어 직선의 방정식 문제라면 보통 다음 순서로 풀어요.

1. 기울기 m을 확인한다.
2. 지나는 점 (x1, y1)을 확인한다.
3. 공식 y - y1 = m(x - x1)에 대입한다.
4. 식을 정리한다.

하브루타 질문:
왜 기울기와 한 점만 알아도 직선의 방정식을 하나로 정할 수 있을까요?

꼬리질문:
이번에는 네가 직접 기울기가 3이고 점 (1, 2)를 지나는 직선의 방정식을 세워볼래?
""".strip()

    return answer


def run_local_rag_tutor(question: str):
    contexts = search_math_context(question, top_k=3)
    answer = make_local_tutor_answer(question, contexts)

    print("=" * 80)
    print("로컬 RAG 튜터 응답")
    print("=" * 80)
    print(answer)

    print()
    print("=" * 80)
    print("참고로 검색된 문서 목록")
    print("=" * 80)

    for i, ctx in enumerate(contexts):
        print(f"{i + 1}. {ctx['id']} / 거리: {ctx['distance']:.4f} / 파일: {ctx['metadata'].get('file')}")


if __name__ == "__main__":
    print("고1 수학 로컬 RAG 튜터입니다.")
    print("종료하려면 q 또는 quit을 입력하세요.")
    print()

    while True:
        user_question = input("질문을 입력하세요: ").strip()

        if user_question.lower() in ["q", "quit", "exit"]:
            print("튜터를 종료합니다.")
            break

        if not user_question:
            print("질문을 입력해주세요.")
            continue

        run_local_rag_tutor(user_question)
        print()
