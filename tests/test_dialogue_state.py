import pytest

from app.rag.dialogue import DialogueState, TutorTurn, prepare_state, restore_state, apply_assessment
from app.rag import tutor
from app.rag.retriever import SearchResult


FOCUS = "useful과 convenient는 각각 어떤 상황에서 쓰면 좋을까요?"


def model_turn(**changes):
    values = dict(explanation="useful은 도움, convenient는 이용의 편리함에 초점을 둡니다.",
                  next_question="도움이 되는 설명에는 어떤 단어가 어울릴까요?",
                  assessment="partial", evidence_quote="", reasoning="두 표현의 차이를 확인합니다.",
                  misconception="", source_ids=["english-1"])
    return TutorTurn(**{**values, **changes})


def history_for(state):
    return [{"sender_type": "ai", "content": state.last_question,
             "response_meta": {"dialogue_state": state.model_dump()}}]


@pytest.mark.parametrize("answer,intent", [
    ("몰라", "hint"), ("어떤 부분부터 생각해야 할지 아직 잘 모르겠고 설명해줘", "hint"),
    ("네", "acknowledgement"), ("알겠어요", "acknowledgement"), ("왜 그런 거야?", "question"),
])
def test_non_answers_cannot_advance_even_if_model_claims_understanding(answer, intent):
    state = prepare_state(history_for(DialogueState(focus_question=FOCUS, last_question=FOCUS)), "영어", answer)
    apply_assessment(state, model_turn(assessment="understood", evidence_quote=answer), answer, {"english-1"})
    assert state.stage == "개념 설명"
    assert state.assessment == "unassessed"
    assert state.last_intent == intent
    assert state.focus_question == FOCUS
    assert not state.evidence


@pytest.mark.parametrize("quote,sources", [("없는 답변", ["english-1"]), ("도움", ["invented"]), ("", ["english-1"]), ("도움", [])])
def test_invalid_evidence_cannot_advance(quote, sources):
    state = prepare_state([], "영어", "도움")
    apply_assessment(state, model_turn(assessment="understood", evidence_quote=quote, source_ids=sources), "도움", {"english-1"})
    assert state.stage == "개념 설명"
    assert state.assessment == "unassessed"


def test_short_answer_can_advance_with_attributed_provisional_evidence():
    state = prepare_state([], "useful의 뜻", "도움이 되는")
    turn = model_turn(assessment="understood", evidence_quote="도움이 되는")
    apply_assessment(state, turn, "도움이 되는", {"english-1"})
    assert state.stage == "근거 확인"
    assert state.evidence[0]["quote"] == "도움이 되는"
    assert state.evidence[0]["verified_by_human"] is False
    assert state.focus_question == turn.next_question


def test_long_wrong_answer_does_not_advance_and_persists_misconception():
    answer = "useful과 convenient는 완전히 같은 뜻이라고 생각하기 때문입니다." * 10
    state = prepare_state([], "영어", answer)
    apply_assessment(state, model_turn(assessment="misconception", misconception="두 표현의 의미를 동일시함"), answer, {"english-1"})
    assert state.stage == "개념 설명"
    restored = restore_state(history_for(state))
    assert restored.misconception == "두 표현의 의미를 동일시함"


def test_reasoning_starting_with_because_is_not_a_question():
    state = prepare_state([], "기관", "왜냐하면 여러 조직이 함께 기능하기 때문입니다.")
    assert state.last_intent == "answer"


def test_legacy_and_invalid_state_restore_conservatively():
    history = [{"sender_type": "user", "content": "길게 설명"}] * 20
    history.append({"sender_type": "ai", "content": FOCUS, "response_meta": {"dialogue_state": {"version": 99}}})
    state = restore_state(history)
    assert state.stage == "개념 설명"
    assert state.focus_question == FOCUS


def test_repeated_hint_keeps_original_focus_not_generic_last_question(monkeypatch):
    state = DialogueState(focus_question=FOCUS, last_question="어떤 단어인지 골라볼까요?", hint_count=1)
    captured = {}
    def fake_search(_db, query, **kwargs):
        captured["query"] = query
        captured["rerank_query"] = kwargs["rerank_query"]
        return []
    def fake_generate(prompt, *args):
        captured["prompt"] = prompt
        return model_turn(assessment="unassessed", source_ids=[]).model_dump_json(), "openai"
    monkeypatch.setattr(tutor, "search", fake_search)
    monkeypatch.setattr(tutor, "generate_with_provider", fake_generate)
    _, feedback, _, meta = tutor.tutor_reply(None, "영어 표현", "몰라", conversation_history=history_for(state))
    assert FOCUS in captured["query"] and FOCUS in captured["rerank_query"]
    assert "몰라" not in captured["query"]
    assert "누적 힌트 횟수: 2" in captured["prompt"]
    assert "핵심을 직접 설명" in captured["prompt"]
    assert meta["dialogue_state"]["hint_count"] == 2
    assert meta["dialogue_state"]["focus_question"] == FOCUS
    assert feedback["followup_question"] == meta["dialogue_state"]["last_question"]


@pytest.mark.parametrize("output", [None, '{"explanation":', '{}', 'plain text', '[]'])
def test_missing_or_invalid_structured_output_falls_back_without_losing_state(monkeypatch, output):
    state = DialogueState(stage="근거 확인", focus_question=FOCUS, last_question=FOCUS)
    monkeypatch.setattr(tutor, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *args: (output, "openai"))
    reply, _, _, meta = tutor.tutor_reply(None, "영어", "몰라", conversation_history=history_for(state))
    assert meta["ai_provider"] == "rule"
    assert meta["stage"] == "근거 확인"
    assert meta["dialogue_state"]["focus_question"] == FOCUS
    assert "방금 질문" in reply
    assert not reply.startswith("{")


def test_state_is_saved_restored_and_isolated_between_sessions(client, auth_headers, monkeypatch):
    context = SearchResult(None, "english-1", "useful: 도움이 되는", 0.8,
                           {"retriever": "chroma", "question": "useful은 무슨 뜻인가요?"})
    monkeypatch.setattr(tutor, "search", lambda *args, **kwargs: [context])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *args: (
        model_turn(assessment="understood", evidence_quote="도움이 되는").model_dump_json(), "openai"))
    room = client.post("/rooms", headers=auth_headers, json={"title": "영어", "subject": "영어"}).json()["room"]
    def create():
        return client.post("/sessions", headers=auth_headers, json={"room_id": room["id"], "topic": "useful"}).json()["session"]["id"]
    first, second = create(), create()
    sent = client.post(f"/sessions/{first}/messages", headers=auth_headers, json={"content": "도움이 되는"})
    assert sent.status_code == 200
    meta = sent.json()["response_meta"]
    assert meta["stage"] == "근거 확인"
    restored = client.get(f"/sessions/{first}", headers=auth_headers).json()
    assert restored["response_meta"]["dialogue_state"] == meta["dialogue_state"]
    assert restored["session"]["messages"][-1]["response_meta"]["dialogue_state"] == meta["dialogue_state"]
    other = client.get(f"/sessions/{second}", headers=auth_headers).json()
    assert other["response_meta"]["stage"] == "개념 설명"
    assert not other["response_meta"]["dialogue_state"]["evidence"]


def test_structured_schema_is_sent_and_incomplete_response_is_rejected(monkeypatch):
    from app.database.config import settings
    captured = {}
    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"status": "incomplete", "output_text": '{"explanation":'})()
    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(tutor, "OpenAI", Client)
    assert tutor._openai_generate("prompt", response_schema=TutorTurn.model_json_schema()) is None
    assert captured["text"]["format"]["strict"] is True
    assert captured["text"]["format"]["schema"]["additionalProperties"] is False
