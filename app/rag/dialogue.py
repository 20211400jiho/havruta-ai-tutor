"""Versioned dialogue snapshots persisted in Message.response_meta_json.

Model assessments are provisional, never objective mastery scores. The server owns
stage transitions; hints, acknowledgements and questions cannot advance a stage.
"""
import re
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

STAGES = ("개념 설명", "근거 확인", "생각 수정", "적용", "최종 정리")
STAGE_GOALS = {
    "개념 설명": "핵심 개념을 자신의 말로 설명하기",
    "근거 확인": "설명한 내용의 이유와 근거 제시하기",
    "생각 수정": "반례를 검토하고 설명을 수정·보완하기",
    "적용": "새로운 사례나 문제에 개념 적용하기",
    "최종 정리": "배운 내용을 자신의 말로 다시 정리하기",
}


class TutorTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    explanation: str = Field(min_length=1, max_length=4000)
    next_question: str = Field(min_length=1, max_length=500)
    assessment: Literal["understood", "partial", "misconception", "unassessed"]
    evidence_quote: str = Field(max_length=1000)
    reasoning: str = Field(min_length=1, max_length=600)
    misconception: str = Field(max_length=600)
    source_ids: list[str] = Field(max_length=3)

    @field_validator("explanation", "next_question", "reasoning")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tutor text cannot be blank")
        return value.strip()


QUESTION_GOALS = {
    "개념 설명": "concept", "근거 확인": "reason", "생각 수정": "counterexample",
    "적용": "application", "최종 정리": "summary",
}


class ProgressiveTutorTurn(TutorTurn):
    next_question_goal: Literal["concept", "reason", "counterexample", "application", "summary", "scaffold", "review"]


class DialogueState(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: Literal[1] = 1
    stage: Literal["개념 설명", "근거 확인", "생각 수정", "적용", "최종 정리"] = "개념 설명"
    learning_goal: str = Field(default="", max_length=1000)
    focus_question: str = Field(default="", max_length=1000)
    last_question: str = Field(default="", max_length=1000)
    hint_count: int = Field(default=0, ge=0, le=10000)
    last_intent: str = "start"
    assessment: str = "unassessed"
    misconception: str = Field(default="", max_length=600)
    evidence: list[dict] = Field(default_factory=list, max_length=5)
    transition_reason: str = "아직 이해를 확인하지 않았습니다."
    stage_turns: int = Field(default=0, ge=0, le=10000)
    recent_questions: list[str] = Field(default_factory=list, max_length=8)
    answered_questions: list[str] = Field(default_factory=list, max_length=8)
    question_goal: str = ""
    question_guard: str = ""


def extract_question(text: str) -> str:
    questions = re.findall(r"[^\n.!?]*[?？]", text)
    if questions:
        return questions[-1].strip()[:1000]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:1000] if lines else ""


def restore_state(history: list[dict]) -> DialogueState:
    for message in reversed(history):
        if message.get("sender_type") != "ai":
            continue
        meta = message.get("response_meta") or {}
        saved = meta.get("dialogue_state") if isinstance(meta, dict) else None
        if isinstance(saved, dict):
            try:
                return DialogueState.model_validate(saved)
            except ValidationError:
                pass
        # Legacy/corrupt metadata: keep the most recent question, do not infer mastery from turns.
        question = extract_question(str(message.get("content") or ""))
        stage = meta.get("stage") if isinstance(meta, dict) else None
        return DialogueState(stage=stage if stage in STAGES else STAGES[0],
                             focus_question=question, last_question=question)
    return DialogueState()


def classify_intent(answer: str) -> str:
    normalized = re.sub(r"[\s.!?~？]+", "", answer).lower()
    if any(marker in normalized for marker in (
        "몰라", "모르겠", "잘모르", "이해가안", "이해안", "이해못", "어려워",
        "어렵다", "힌트", "도와줘", "설명해줘", "다시설명",
    )):
        return "hint"
    if normalized in {"응", "네", "예", "ㅇㅇ", "알겠어", "알겠습니다", "그래", "맞아", "알겠어요"}:
        return "acknowledgement"
    if ("?" in answer or "？" in answer
            or (normalized.startswith("왜") and not normalized.startswith("왜냐하면"))
            or normalized.startswith(("어떻게", "무슨", "뭐야", "뭔뜻"))
            or normalized.endswith(("뭐야", "뭔가요", "인가요", "알려줘"))):
        return "question"
    return "answer"


def prepare_state(history: list[dict], topic: str, answer: str) -> DialogueState:
    state = restore_state(history).model_copy(deep=True)
    state.focus_question = state.focus_question or f"{topic}의 핵심 개념은 무엇인가요?"[:1000]
    state.last_question = state.last_question or state.focus_question
    state.learning_goal = state.learning_goal or state.focus_question
    if not state.recent_questions:
        state.recent_questions = [extract_question(str(item.get("content") or ""))
                                  for item in history if item.get("sender_type") == "ai"][-8:]
    state.stage_turns = min(state.stage_turns + 1, 10000)
    state.question_guard = ""
    state.last_intent = classify_intent(answer)
    if state.last_intent == "hint":
        state.hint_count = min(state.hint_count + 1, 10000)
    return state


def apply_assessment(state: DialogueState, turn: TutorTurn, answer: str, source_ids: set[str]) -> None:
    state.assessment = turn.assessment if state.last_intent == "answer" else "unassessed"
    supported = bool(turn.source_ids) and set(turn.source_ids).issubset(source_ids)
    quoted = bool(turn.evidence_quote.strip()) and turn.evidence_quote in answer
    # Choosing an option can establish recall, but not reasoning or transfer.
    choice_only = bool(re.fullmatch(r"\s*(?:[1-9]|[①②③④⑤⑥⑦⑧⑨])\s*(?:번)?[.!]?\s*", answer))
    if choice_only and state.stage != STAGES[0] and turn.assessment == "understood":
        state.assessment = "partial"
        quoted = False
    state.transition_reason = "이해 확인이 충분하지 않아 현재 단계를 유지합니다."
    if state.last_intent == "answer" and turn.assessment == "misconception":
        state.misconception = turn.misconception
    if state.last_intent == "answer" and turn.assessment == "understood" and quoted and supported:
        # Updating a final-stage answer must not evict earlier-stage evidence.
        state.evidence = ([item for item in state.evidence if item.get("stage") != state.stage] + [{
            "stage": state.stage, "quote": turn.evidence_quote,
            "question": state.last_question,
            "reasoning": turn.reasoning, "source_ids": turn.source_ids,
            "assessment_provider": "openai", "verified_by_human": False,
        }])[-5:]
        state.answered_questions = (state.answered_questions + [state.last_question])[-8:]
        state.stage = STAGES[min(STAGES.index(state.stage) + 1, len(STAGES) - 1)]
        state.focus_question = turn.next_question
        state.hint_count = 0
        state.stage_turns = 0
        state.misconception = ""
        state.transition_reason = "학생 인용과 검색 출처가 있는 AI 이해 판단에 따라 한 단계 진행합니다."
    elif turn.assessment == "understood" and state.assessment != "partial":
        state.assessment = "unassessed"
    state.last_question = turn.next_question


def question_repeats(question: str, previous: list[str]) -> bool:
    """Lexical similarity guard; does not prove semantic equivalence."""
    normalized = re.sub(r"[^가-힣a-z0-9]", "", question.lower())
    if not normalized:
        return True
    return any(SequenceMatcher(None, normalized, old).ratio() >= 0.78
               for text in previous
               if (old := re.sub(r"[^가-힣a-z0-9]", "", text.lower())))


def select_followup(state: DialogueState, turn: ProgressiveTutorTurn, topic: str) -> str:
    """Enforce question purpose without inventing mastery or domain facts."""
    completed = state.stage == STAGES[-1] and any(item.get("stage") == STAGES[-1] for item in state.evidence)
    expected = "review" if completed else QUESTION_GOALS[state.stage]
    supported = state.last_intent != "answer" or state.assessment != "understood"
    allowed = {expected, "scaffold"} if supported else {expected}
    repeated = question_repeats(turn.next_question, state.recent_questions + state.answered_questions)
    if turn.next_question_goal in allowed and not repeated:
        question, goal = turn.next_question, turn.next_question_goal
    else:
        state.question_guard = "반복 질문 교체" if repeated else "단계에 맞는 질문으로 교체"
        anchor = next((str(item.get("quote") or "") for item in reversed(state.evidence)
                       if item.get("quote")), topic)[:180]
        options = {
            "concept": [f"‘{topic}’과 관련해 알고 있는 구체적인 사례 하나를 자신의 말로 설명해볼까요?",
                        f"‘{topic}’에서 이해한 점과 아직 헷갈리는 점을 하나씩 이야기해볼까요?"],
            "reason": [f"‘{anchor}’라고 설명한 이유를 사례 하나와 연결해 말해볼까요?",
                       f"‘{anchor}’라는 설명을 확인하려면 어떤 관찰이나 근거가 필요할까요?"],
            "counterexample": [f"‘{anchor}’라는 설명이 적용되지 않는 경우가 있을지 예를 들어 생각해볼까요?",
                               f"‘{anchor}’라는 설명에 조건을 하나 덧붙인다면 어떻게 보완할 수 있을까요?"],
            "application": [f"‘{anchor}’를 활용할 수 있는 새로운 상황 하나를 정해 어떻게 적용할지 설명해볼까요?",
                            f"‘{anchor}’를 친구가 겪는 문제에 적용한다면 어떤 도움을 줄 수 있을까요?"],
            "summary": ["이번 대화에서 이해한 개념과 그 이유, 적용 사례를 자신의 말로 연결해 정리해볼까요?",
                        "처음 생각에서 달라진 점과 아직 궁금한 점을 정리해볼까요?"],
            "review": ["이번 대화는 여기서 마무리해도 좋아요. 더 알아보고 싶은 점이나 복습하고 싶은 부분이 있나요?",
                       "학습 종료로 기록을 남기거나 다른 단원으로 넘어갈까요?"],
        }
        question = next((q for q in options[expected] if not question_repeats(q, state.recent_questions)),
                        "지금까지 설명 중 어느 부분에서 막혔는지 짚어주면 그 부분부터 함께 풀어볼까요?")
        goal = expected
    state.question_goal = goal
    state.last_question = question
    state.recent_questions = (state.recent_questions + [question])[-8:]
    if state.assessment == "understood":
        state.focus_question = question
    return question


def learning_report(history: list[dict], topic: str) -> dict:
    """Observable learning evidence, not a validated learning-effectiveness score."""
    state = restore_state(history)
    evidence = {item.get("stage"): item for item in state.evidence if item.get("stage") in STAGES}
    answers = [str(item.get("content") or "").strip() for item in history
               if item.get("sender_type") == "user" and str(item.get("content") or "").strip()
               and classify_intent(str(item.get("content") or "")) == "answer"]
    objectives = [{
        "stage": stage, "description": description,
        "status": "ai_checked" if stage in evidence else "not_checked",
        "evidence_quote": evidence.get(stage, {}).get("quote"),
        "question": evidence.get(stage, {}).get("question"),
        "source_ids": evidence.get(stage, {}).get("source_ids", []),
    } for stage, description in STAGE_GOALS.items()]
    remaining = [item["description"] for item in objectives if item["status"] == "not_checked"]
    return {
        "topic": topic, "learning_goal": state.learning_goal or state.focus_question or topic,
        "stage": state.stage, "objectives": objectives,
        "checked_count": len(evidence), "total_count": len(STAGES),
        "first_explanation": answers[0] if answers else None,
        "latest_explanation": answers[-1] if answers else None,
        "has_comparison": len(answers) >= 2,
        "misconception": state.misconception or None,
        "next_review": state.misconception or (remaining[0] if remaining else "시간을 두고 다른 문제로 다시 확인하기"),
        "notice": "AI의 잠정적 확인 기록입니다. 미확인은 오답이 아니며, 학습효과나 단원 전체 숙달을 증명하지 않습니다.",
    }
