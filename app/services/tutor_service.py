import json
from urllib import error, request

from sqlalchemy.orm import Session

from app.database.config import settings
from app.services.rag_service import SearchResult, search, tokenize


def _ollama_generate(prompt: str) -> str | None:
    if settings.ai_provider != "ollama":
        return None
    payload = json.dumps({"model": settings.ollama_model, "prompt": prompt, "stream": False}).encode()
    req = request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode()).get("response")
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def initial_question(db: Session, topic: str) -> tuple[str, list[SearchResult]]:
    contexts = search(db, topic, top_k=1)
    if contexts and contexts[0].metadata.get("question"):
        question = contexts[0].metadata["question"]
        return f"오늘은 ‘{topic}’을 함께 탐구해볼게요. 먼저 생각을 말해보세요.\n\n{question}", contexts
    return f"오늘은 ‘{topic}’을 하브루타 방식으로 공부해볼게요. 이 주제에서 이미 알고 있는 내용을 설명해줄래요?", []


def evaluate_answer(answer: str, context: SearchResult | None) -> dict:
    answer_tokens = tokenize(answer)
    expected = context.metadata.get("answer", "") if context else ""
    expected_tokens = tokenize(expected)
    overlap = len(answer_tokens & expected_tokens)
    score = min(95, 50 + min(len(answer), 80) // 4 + overlap * 8)
    if len(answer) < 12:
        improvements = "답의 근거나 풀이 과정을 한 문장 더 설명해보세요."
    elif expected_tokens and not overlap:
        improvements = "핵심 조건과 결론이 어떻게 연결되는지 다시 확인해보세요."
    else:
        improvements = "같은 결론을 다른 표현이나 식으로도 설명해보세요."
    strengths = "자신의 언어로 답을 구성했습니다."
    if overlap:
        strengths = "학습 자료의 핵심 개념을 정확히 포함했습니다."
    return {
        "score": score,
        "summary": "답변의 핵심 개념과 설명 충실도를 기준으로 평가했습니다.",
        "strengths": strengths,
        "improvements": improvements,
    }


def tutor_reply(db: Session, topic: str, answer: str) -> tuple[str, dict, list[SearchResult]]:
    contexts = search(db, f"{topic} {answer}", top_k=3)
    context = contexts[0] if contexts else None
    feedback = evaluate_answer(answer, context)
    followup = (
        context.metadata.get("question")
        if context and context.metadata.get("question") and context.metadata.get("question") not in answer
        else f"‘{topic}’의 핵심 원리를 예시를 들어 설명할 수 있을까요?"
    )
    feedback["followup_question"] = followup
    reference = context.metadata.get("description", "") if context else ""
    prompt = (
        "당신은 고등학생과 문답하는 하브루타 수학 튜터입니다. 정답을 바로 말하기보다 "
        "학생 답변을 짧게 평가하고 다음 사고를 이끄는 질문을 하세요.\n"
        f"주제: {topic}\n학생 답변: {answer}\n참고 자료: {reference}\n"
    )
    generated = _ollama_generate(prompt)
    if generated:
        return generated.strip(), feedback, contexts
    reference_text = f"\n\n참고 개념: {reference}" if reference else ""
    reply = (
        f"좋아요. {feedback['strengths']}\n"
        f"보완할 점: {feedback['improvements']}"
        f"{reference_text}\n\n다음 질문: {followup}"
    )
    return reply, feedback, contexts
