import pytest

from app.rag import tutor
from app.rag.dialogue import DialogueState, ProgressiveTutorTurn, apply_assessment, prepare_state, restore_state
from app.rag.hints import build_hint, tutor_response_schema
from app.rag.retriever import SearchResult

QUESTION = "산업단지의 하천 오염을 줄이려면 무엇을 확인해야 할까요?"


def history(state):
    return [{"sender_type": "ai", "content": QUESTION,
             "response_meta": {"dialogue_state": state.model_dump()}}]


def turn(**changes):
    fields = dict(explanation="폐수 처리 시설이 정답입니다.", next_question="공장에서 나온 물은 어디로 흘러갈까요?",
                  assessment="partial", evidence_quote="", reasoning="설명을 추가 확인합니다.",
                  misconception="", source_ids=["environment-1"], next_question_goal="scaffold",
                  hint_keywords=["공장에서 나온 물", "하천에 보내기 전"],
                  hint_text="물이 하천에 도착하기 전에 어떤 과정을 거쳐야 할지 생각해보세요.")
    return ProgressiveTutorTurn(**{**fields, **changes})


def reply(monkeypatch, state, answer, generated=None):
    context = SearchResult(None, "environment-1", "환경 보호를 위한 시설과 수질 관리가 필요합니다.", .8,
                           {"retriever": "chroma", "description": "폐수 처리 시설이 정답입니다."})
    monkeypatch.setattr(tutor, "search", lambda *args, **kwargs: [context])
    model = generated or turn()
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *args: (model.model_dump_json(), "openai"))
    return tutor.tutor_reply(None, "자연환경과 인간", answer, "사회", conversation_history=history(state))


def test_explicit_help_shows_cues_without_answer_or_check(monkeypatch):
    state = DialogueState(stage="적용", focus_question=QUESTION, last_question=QUESTION)
    text, feedback, _, meta = reply(monkeypatch, state, "모르겠어요",
                                  turn(assessment="understood", evidence_quote="모르겠어요"))
    assert "폐수 처리 시설" not in text
    assert "정답 대신" in text
    assert meta["hint"]["trigger"] == "requested"
    assert meta["hint"]["keywords"] == ["공장에서 나온 물", "하천에 보내기 전"]
    assert meta["hint"]["level"] == 1
    assert meta["stage"] == "적용"
    assert meta["dialogue_state"]["evidence"] == []
    assert feedback["assessment"] == "unassessed"


def test_third_nonprogressing_turn_automatically_shows_hint(monkeypatch):
    state = DialogueState(stage="근거 확인", focus_question=QUESTION, last_question=QUESTION, stage_turns=2)
    text, _, _, meta = reply(monkeypatch, state, "그냥 좋아 보여요")
    assert meta["hint"]["trigger"] == "stalled"
    assert meta["dialogue_state"]["stage_turns"] == 3
    assert not meta["dialogue_state"]["evidence"]
    assert "폐수 처리 시설" not in text


def test_no_automatic_hint_before_threshold(monkeypatch):
    state = DialogueState(focus_question=QUESTION, last_question=QUESTION, stage_turns=1)
    _, _, _, meta = reply(monkeypatch, state, "아직 잘 정리하지 못했어요")
    assert meta["hint"] is None
    assert meta["dialogue_state"]["scaffold_count"] == 0


def test_help_after_previous_understanding_enables_hint_prompt(monkeypatch):
    state = DialogueState(stage="적용", focus_question=QUESTION, last_question=QUESTION,
                          assessment="understood")
    captured = {}
    monkeypatch.setattr(tutor, "search", lambda *a, **kw: [])
    def generate(prompt, *args):
        captured["prompt"] = prompt
        return turn(assessment="unassessed", source_ids=[]).model_dump_json(), "openai"
    monkeypatch.setattr(tutor, "generate_with_provider", generate)
    _, _, _, meta = tutor.tutor_reply(None, "환경", "모르겠어요", conversation_history=history(state))
    assert "힌트 지원 모드: 켜짐" in captured["prompt"]
    assert meta["hint"]["trigger"] == "requested"
    assert meta["stage"] == "적용"


def test_real_understanding_advances_instead_of_showing_stalled_hint(monkeypatch):
    answer = "오염이 하천 생물의 서식지를 훼손할 수 있기 때문입니다."
    state = DialogueState(stage="근거 확인", focus_question=QUESTION, last_question=QUESTION,
                          stage_turns=2, scaffold_count=2, last_hint_keywords=["공장에서 나온 물"])
    _, _, _, meta = reply(monkeypatch, state, answer, turn(assessment="understood", evidence_quote=answer))
    assert meta["stage"] == "생각 수정"
    assert meta["hint"] is None
    assert meta["dialogue_state"]["scaffold_count"] == 0
    assert meta["dialogue_state"]["last_hint_keywords"] == []
    assert len(meta["dialogue_state"]["evidence"]) == 1


def test_hint_levels_persist_and_cap_at_three():
    state = prepare_state(history(DialogueState(stage="적용", focus_question=QUESTION, last_question=QUESTION)), "환경", "몰라")
    for level in [1, 2, 3, 3]:
        hint = build_hint(state, turn())
        assert hint["level"] == level
        state = restore_state(history(state))
    assert state.stage == "적용" and not state.evidence


def test_copying_hint_keyword_does_not_complete_application():
    state = prepare_state(history(DialogueState(stage="적용", focus_question=QUESTION, last_question=QUESTION,
                                               last_hint_keywords=["공장에서 나온 물"])), "환경", "공장에서 나온 물")
    apply_assessment(state, turn(assessment="understood", evidence_quote="공장에서 나온 물"),
                     "공장에서 나온 물", {"environment-1"})
    assert state.stage == "적용" and not state.evidence
    assert state.assessment == "partial"


def test_provider_failure_uses_safe_hint_not_full_reference_answer(monkeypatch):
    state = DialogueState(stage="적용", focus_question=QUESTION, last_question=QUESTION)
    monkeypatch.setattr(tutor, "search", lambda *a, **kw: [SearchResult(None, "source", "본문", .8, {"description": "폐수 처리 시설이 정답입니다."})])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *a: (None, "rule"))
    text, _, _, meta = tutor.tutor_reply(None, "환경", "몰라", conversation_history=history(state))
    assert meta["ai_provider"] == "rule" and meta["hint"]
    assert "폐수 처리 시설" not in text
    assert meta["hint"]["keywords"] == ["배운 개념", "새로운 상황", "판단 이유"]
    assert meta["stage"] == "적용"


def test_completed_learning_does_not_trigger_stalled_hint():
    state = DialogueState(stage="최종 정리", last_intent="hint", stage_turns=10,
                          evidence=[{"stage": "최종 정리"}])
    assert build_hint(state, turn()) is None


def test_strict_schema_requires_hint_fields_but_legacy_model_still_loads():
    schema = tutor_response_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert "default" not in schema["properties"]["hint_text"]
    old = turn().model_dump(exclude={"hint_keywords", "hint_text"})
    assert ProgressiveTutorTurn.model_validate(old).hint_keywords == []


@pytest.mark.parametrize("words", [["키워드"] * 4, ["아" * 25]])
def test_hint_fields_are_bounded(words):
    with pytest.raises(ValueError):
        turn(hint_keywords=words)
