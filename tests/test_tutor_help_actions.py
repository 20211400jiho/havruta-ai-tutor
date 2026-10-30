import pytest

from app.models.chat import Message
from app.rag import tutor
from app.rag.dialogue import DialogueState, ProgressiveTutorTurn, apply_assessment, classify_intent, learning_report, prepare_state
from app.rag.hints import needs_hint
from app.rag.retriever import SearchResult
from conftest import TestSession

QUESTION = "개발이 필요한 경우 어떤 조건을 함께 고려해야 할까요?"
EXAMPLE = "가상의 예로 학교 운동장에 새 시설을 만드는 상황을 생각해보세요. 편리해지는 점뿐 아니라 주변 공간을 이용하는 사람에게 미치는 영향도 함께 살펴볼 수 있어요."


def history(state):
    return [{"sender_type": "ai", "content": QUESTION, "response_meta": {"dialogue_state": state.model_dump()}}]


def model_turn(**changes):
    values = dict(explanation=EXAMPLE, next_question="시설이 생기면 누구의 생활이 달라질 수 있을까요?",
                  assessment="understood", evidence_quote="자연과 인간은 서로 영향을 줍니다.", reasoning="현재 개념을 설명합니다.",
                  misconception="", source_ids=["environment-1"], next_question_goal="application",
                  hint_keywords=["편리함", "다른 사람의 생활"], hint_text="영향을 받는 대상을 하나씩 떠올려보세요.")
    return ProgressiveTutorTurn(**{**values, **changes})


def mocked_model(monkeypatch, turn=None):
    captured = {}
    def search(db, query, *args, **kwargs):
        captured["query"] = query
        captured["rerank_query"] = kwargs.get("rerank_query", "")
        return [SearchResult(None, "environment-1", "개발은 환경과 주변 사람에게 영향을 미칠 수 있습니다.", .8,
                             {"retriever": "chroma", "description": "폐수 처리 시설이 정답입니다."})]
    def generate(prompt, *args):
        captured["prompt"] = prompt
        return (turn or model_turn()).model_dump_json(), "openai"
    monkeypatch.setattr(tutor, "search", search)
    monkeypatch.setattr(tutor, "generate_with_provider", generate)
    return captured


@pytest.mark.parametrize("text", ["지금 질문을 쉬운 예시로 설명해 주세요.", "예시로 설명해줘", "예를 들어 설명해줘", "쉬운 사례 하나만 보여주세요"])
def test_natural_example_request_is_not_an_answer(text):
    assert classify_intent(text) == "example"


@pytest.mark.parametrize("text", ["쉽게 설명", "쉽게 설명해줘", "지금 내용을 쉬운 말로 다시 설명해 주세요.", "쉽게 풀어줘"])
def test_simplification_request_is_distinct_from_hint_and_example(text):
    assert classify_intent(text) == "simplify"


def test_student_explaining_their_own_example_remains_an_answer():
    assert classify_intent("댐을 예시로 설명하면, 물을 얻는 이익과 생태계 피해를 함께 고려해야 합니다.") == "answer"


@pytest.mark.parametrize("action", ["hint", "example", "simplify"])
def test_explicit_help_never_checks_a_goal_even_if_model_says_understood(monkeypatch, action):
    state = DialogueState(stage="생각 수정", focus_question=QUESTION, last_question=QUESTION,
                          evidence=[{"stage": "개념 설명", "quote": "처음 설명"}])
    captured = mocked_model(monkeypatch)
    text, feedback, _, meta = tutor.tutor_reply(None, "자연환경과 인간", "자연과 인간은 서로 영향을 줍니다.", "사회",
                                               conversation_history=history(state), help_action=action)
    assert meta["help_action"] == action and meta["stage"] == state.stage
    assert meta["dialogue_state"]["evidence"] == state.evidence
    assert meta["dialogue_state"]["focus_question"] == QUESTION
    assert feedback["assessment"] == "unassessed"
    assert QUESTION in captured["query"] and QUESTION in captured["rerank_query"]
    assert "자연과 인간은 서로 영향을 줍니다." not in captured["query"]
    if action == "hint":
        assert meta["hint"] and meta["hint"]["trigger"] == "requested"
        assert EXAMPLE not in text
    elif action == "example":
        assert EXAMPLE in text and meta["hint"] is None
        assert "이번 응답은 예시 설명 모드" in captured["prompt"]
        assert "다른 유사 사례" in captured["prompt"]
        assert "변수의 의미·단위·초기값" in captured["prompt"]
    else:
        assert meta["hint"] is None
        assert "이번 응답은 쉽게 설명 모드" in captured["prompt"]
        assert "더 쉬운 별개 문제로 되돌리지" in captured["prompt"]
        assert "고정 계수와 변하는 값을 혼동하지" in captured["prompt"]
    assert meta["answer_status"] == "unassessed"


def test_example_mode_is_not_replaced_by_automatic_hint_after_three_turns(monkeypatch):
    mocked_model(monkeypatch)
    state = DialogueState(stage="적용", focus_question=QUESTION, last_question=QUESTION, stage_turns=5)
    text, _, _, meta = tutor.tutor_reply(None, "환경", "예시로 설명해줘", "사회", conversation_history=history(state))
    assert EXAMPLE in text and meta["hint"] is None and meta["help_action"] == "example"
    assert meta["dialogue_state"]["example_count"] == 1
    assert not needs_hint(DialogueState.model_validate(meta["dialogue_state"]))


def test_example_failure_is_honest_and_keeps_learning_state(monkeypatch):
    mocked_model(monkeypatch)
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *args: (None, "rule"))
    state = DialogueState(stage="적용", focus_question=QUESTION, last_question="어떤 대상이 영향을 받을까요?")
    text, feedback, _, meta = tutor.tutor_reply(None, "환경", "예시로 설명해줘", "사회", conversation_history=history(state))
    assert "예시 설명을 생성하지 못했어요" in text and "폐수 처리 시설" not in text
    assert meta["ai_provider"] == "rule" and meta["hint"] is None
    assert meta["stage"] == "적용" and feedback["assessment"] == "unassessed"
    assert state.last_question in text
    assert meta["dialogue_state"]["last_question"] == state.last_question
    assert feedback["followup_question"] == state.last_question


def test_help_request_text_is_excluded_from_report_even_if_it_looks_like_an_answer():
    report = learning_report([
        {"sender_type": "user", "content": "자연과 인간은 서로 영향을 줍니다.", "response_meta": {"help_action": "example"}},
        {"sender_type": "user", "content": "예시로 설명해줘"},
    ], "환경")
    assert report["first_explanation"] is None and report["latest_explanation"] is None


def test_understanding_after_help_can_advance_normally_and_resets_example_count():
    state = prepare_state(history(DialogueState(focus_question=QUESTION, last_question=QUESTION, example_count=2)),
                          "환경", "자연과 인간은 서로 영향을 줍니다.")
    apply_assessment(state, model_turn(), "자연과 인간은 서로 영향을 줍니다.", {"environment-1"})
    assert state.stage == "근거 확인" and len(state.evidence) == 1 and state.example_count == 0


@pytest.mark.parametrize("action", ["hint", "example", "simplify"])
def test_api_help_persists_separately_and_survives_resume(client, auth_headers, monkeypatch, action):
    room = client.post("/rooms/personal", headers=auth_headers, json={"subject": "수학", "grade": "고등학교 1학년"}).json()["room"]
    session = client.post("/sessions", headers=auth_headers, json={"room_id": room["id"], "topic": "도형의 방정식"}).json()["session"]
    mocked_model(monkeypatch)
    response = client.post(f"/sessions/{session['id']}/messages", headers=auth_headers,
                           json={"content": "자연과 인간은 서로 영향을 줍니다.", "help_action": action})
    assert response.status_code == 200
    result = response.json()
    assert result["response_meta"]["help_action"] == action
    assert result["learning_report"]["checked_count"] == 0
    assert result["learning_report"]["first_explanation"] is None
    with TestSession() as db:
        user_message = db.query(Message).filter_by(session_id=session["id"], sender_type="user").one()
        assert user_message.response_meta_json == {"help_action": action}
    client.post(f"/sessions/{session['id']}/pause", headers=auth_headers)
    restored = client.post(f"/sessions/{session['id']}/resume", headers=auth_headers).json()
    assert restored["response_meta"]["help_action"] == action
    assert restored["session"]["learning_report"]["checked_count"] == 0


def test_invalid_help_action_is_rejected(client, auth_headers):
    response = client.post("/sessions/999/messages", headers=auth_headers,
                           json={"content": "힌트를 주세요", "help_action": "give_answer"})
    assert response.status_code == 422


def test_correct_calculation_keeps_acknowledgement_without_checking_whole_stage(monkeypatch):
    question = "y=-2x에서 x가 1에서 3으로 증가할 때, y의 값은 어떻게 변하나요?"
    answer = "y는 -2에서 -6으로 변할 것 같아"
    acknowledgement = "맞아. x가 2만큼 증가할 때 y는 -2에서 -6으로 4만큼 감소했네."
    captured = mocked_model(monkeypatch, model_turn(
        assessment="partial", answer_status="correct", evidence_quote=answer, explanation=acknowledgement,
        next_question="-2와 -6 중 어느 쪽이 더 작나요?", next_question_goal="scaffold",
    ))
    state = DialogueState(focus_question=question, last_question=question, stage_turns=8)
    text, feedback, _, meta = tutor.tutor_reply(None, "일차함수", answer, "수학", conversation_history=history(state))
    assert text.startswith(acknowledgement)
    assert "어느 쪽이 더 작나요" not in text and "개념이나 이유" in text
    assert meta["answer_status"] == "correct" and meta["dialogue_state"]["question_goal"] == "reason"
    assert meta["hint"] is None and meta["stage"] == "개념 설명"
    assert not meta["dialogue_state"]["evidence"] and feedback["assessment"] == "partial"
    assert feedback["level"] == "맞힌 내용에서 이어가기"
    assert "자동 힌트 모드로 바꾸거나 난이도를 낮추지" in captured["prompt"]


def test_correct_subanswer_keeps_natural_concept_followup(monkeypatch):
    answer = "-2에서 -6으로 변해"
    next_question = "식에서 -2라는 수는 이런 변화와 어떻게 연결될까?"
    mocked_model(monkeypatch, model_turn(assessment="partial", answer_status="correct", evidence_quote=answer,
                                         next_question=next_question, next_question_goal="reason"))
    state = DialogueState(focus_question=QUESTION, last_question=QUESTION, stage_turns=10)
    text, _, _, meta = tutor.tutor_reply(None, "일차함수", answer, "수학", conversation_history=history(state))
    assert next_question in text and meta["hint"] is None
    assert meta["answer_status"] == "correct" and not meta["dialogue_state"]["evidence"]


def test_subanswer_status_does_not_bypass_quote_or_source_requirements(monkeypatch):
    mocked_model(monkeypatch, model_turn(assessment="partial", answer_status="correct", evidence_quote="실제 답변에 없는 인용"))
    state = DialogueState(focus_question=QUESTION, last_question=QUESTION)
    _, _, _, meta = tutor.tutor_reply(None, "환경", "내 답변", "사회", conversation_history=history(state))
    assert meta["answer_status"] == "unassessed" and not meta["dialogue_state"]["evidence"]


def test_simplify_failure_keeps_original_question_without_fabricating_explanation(monkeypatch):
    mocked_model(monkeypatch)
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *args: (None, "rule"))
    state = DialogueState(focus_question=QUESTION, last_question=QUESTION, stage_turns=10)
    text, _, _, meta = tutor.tutor_reply(None, "환경", "쉽게 설명해줘", "사회", conversation_history=history(state))
    assert "쉬운 설명을 생성하지 못했어요" in text and QUESTION in text
    assert meta["help_action"] == "simplify" and meta["hint"] is None
    assert meta["dialogue_state"]["last_question"] == QUESTION
