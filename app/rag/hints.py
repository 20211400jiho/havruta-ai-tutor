"""Progressive thinking cues, separate from both answer text and mastery evidence."""
from app.rag.dialogue import ProgressiveTutorTurn, STAGES

AUTO_HINT_AFTER_TURNS = 3

STAGE_CUES = {
    "개념 설명": (["뜻", "특징", "예시"], "정의를 완성하려 하지 말고, 떠오르는 특징 하나를 골라보세요."),
    "근거 확인": (["원인", "결과", "연결"], "지금 설명의 앞뒤를 ‘왜냐하면’으로 연결할 수 있을지 생각해보세요."),
    "생각 수정": (["다른 관점", "조건", "생각의 변화"], "처음 생각에서 빠뜨린 조건이나 영향을 받는 대상을 하나 찾아보세요."),
    "적용": (["배운 개념", "새로운 상황", "판단 이유"], "앞선 사례와 지금 상황의 공통점 하나를 찾고, 그 이유를 연결해보세요."),
    "최종 정리": (["핵심 개념", "근거", "내 말로 정리"], "이번에 알게 된 점 하나와 그렇게 생각하는 이유 하나를 연결해보세요."),
}


def tutor_response_schema() -> dict:
    schema = ProgressiveTutorTurn.model_json_schema()
    # Strict Structured Outputs requires every property even when our Python model
    # accepts legacy payloads without hints. Empty values mean "no hint this turn".
    schema["required"] = list(schema["properties"])
    for field in schema["properties"].values():
        field.pop("default", None)
    return schema


def needs_hint(state) -> bool:
    completed = state.stage == STAGES[-1] and any(
        item.get("stage") == STAGES[-1] for item in state.evidence
    )
    if completed or state.assessment == "understood":
        return False
    return state.last_intent == "hint" or state.stage_turns >= AUTO_HINT_AFTER_TURNS


def build_hint(state, turn: ProgressiveTutorTurn | None) -> dict | None:
    if not needs_hint(state):
        return None
    fallback_keywords, fallback_text = STAGE_CUES[state.stage]
    keywords = turn.hint_keywords if turn and turn.hint_keywords else fallback_keywords
    text = turn.hint_text.strip() if turn and turn.hint_text.strip() else fallback_text
    state.scaffold_count = min(state.scaffold_count + 1, 10000)
    state.last_hint_keywords = list(keywords)
    return {
        "level": min(state.scaffold_count, 3),
        "trigger": "requested" if state.last_intent == "hint" else "stalled",
        "keywords": keywords,
        "text": text,
        "notice": "생각을 돕는 단서예요. 단어를 그대로 쓰기보다 내 생각과 이유를 설명해보세요.",
    }
