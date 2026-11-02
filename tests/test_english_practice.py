import pytest

from app.rag import tutor
from app.rag.dialogue import DialogueState, ProgressiveTutorTurn, STAGES, QUESTION_GOALS, select_followup, learning_report
from app.rag.english_practice import initial_activity, is_theory_question, is_question_form_answer
from app.rag.retriever import SearchResult


SOURCE = SearchResult(None, "english-1", "Tom missed the bus, so he walked to school. He walked because he missed the bus.", .9,
                      {"question": "이해 질문이란 무엇인가요?", "retriever": "chroma"})


def turn(**changes):
    values = dict(explanation="버스를 놓쳐서 걸어갔다는 이유를 정확히 찾았어요.",
                  next_question="Tom missed the bus, so he walked to school. 여기서 이유와 결과를 연결하는 영어 단어는 무엇인가요?",
                  assessment="understood", answer_status="correct", evidence_quote="Because he missed the bus.",
                  reasoning="지문에 나타난 행동의 이유를 설명했습니다.", misconception="", source_ids=["english-1"],
                  next_question_goal="reason")
    return ProgressiveTutorTurn(**{**values, **changes})


def history(question="Why did Tom walk to school?", **changes):
    state = DialogueState(focus_question=question, last_question=question, **changes)
    return [{"sender_type": "ai", "content": "연습용 문장: Tom missed the bus, so he walked to school.\n" + question,
             "response_meta": {"dialogue_state": state.model_dump()}}]


@pytest.mark.parametrize("topic,level,expected", [
    ("영어 이해", "중학교", "Why did Tom"), ("영어 이해", "고등학교", "Why did Mina"),
    ("영어 표현", "중학교", "Can I"), ("영어 표현", "고등학교", "I think"),
])
def test_initial_english_activity_replaces_theory_and_preserves_scope(monkeypatch, topic, level, expected):
    captured = {}
    def search(*args, **kwargs):
        captured.update(kwargs)
        return [SOURCE]
    monkeypatch.setattr(tutor, "search", search)
    text, sources = tutor.initial_question(None, topic, "영어", unit_code="scope-code", school_level=level, grade="1학년")
    assert expected in text and "이해 질문이란" not in text
    assert sources == [SOURCE]
    assert captured == {"top_k": 1, "subject": "영어", "unit_code": "scope-code", "school_level": level, "grade": "1학년"}


def test_other_subject_initial_question_unchanged(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [SOURCE])
    assert "이해 질문이란" in tutor.initial_question(None, "읽기", "국어")[0]


def test_generated_practice_is_available_without_search_but_not_a_fake_source(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [])
    text, sources = tutor.initial_question(None, "영어 이해", "영어")
    assert "연습용 문장" in text and "Tom" in text and sources == []


def test_short_correct_english_answer_advances_only_with_real_quote_and_source(monkeypatch):
    captured = {}
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [SOURCE])
    def generate(prompt, *args):
        captured["prompt"] = prompt
        return turn().model_dump_json(), "openai"
    monkeypatch.setattr(tutor, "generate_with_provider", generate)
    text, feedback, sources, meta = tutor.tutor_reply(None, "영어 이해", "Because he missed the bus.", "영어", conversation_history=history())
    assert meta["stage"] == "근거 확인" and len(meta["dialogue_state"]["evidence"]) == 1
    assert "버스를 놓쳐서" in text and "Tom missed" in text
    assert "영어 과목 전용" in captured["prompt"] and "연습용 문장" in captured["prompt"]
    assert "source_id=english-1" in captured["prompt"] and sources == [SOURCE]
    assert feedback["assessment"] == "understood"


@pytest.mark.parametrize("stage", STAGES)
def test_question_guard_uses_language_activities_in_every_stage(stage):
    state = DialogueState(stage=stage, assessment="partial")
    question = select_followup(state, turn(next_question="‘영어 이해’과 관련해 알고 있는 구체적인 사례를 설명해볼까요?",
                                          next_question_goal=QUESTION_GOALS[stage]), "영어 이해", "영어")
    assert not is_theory_question(question)
    assert any(word in question for word in ("영어", "표현", "구절"))
    assert "구체적인 사례" not in question


def test_old_theory_session_recovers_without_adding_a_check(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [SOURCE])
    def no_model(*args):
        pytest.fail("Theory recovery is a transparent practice template, not an AI grade")
    monkeypatch.setattr(tutor, "generate_with_provider", no_model)
    text, feedback, _, meta = tutor.tutor_reply(None, "영어 이해", "글의 내용을 확인하는 질문입니다.", "영어",
                                               conversation_history=history("이해 질문이란 무엇인가요?"))
    assert "Tom missed" in text and "실제 영어 연습" in text
    assert meta["ai_provider"] == "practice_template" and meta["stage"] == "개념 설명"
    assert meta["dialogue_state"]["evidence"] == [] and feedback["assessment"] == "unassessed"


def test_hint_keeps_english_task_and_never_grades_request(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [SOURCE])
    help_turn = turn(next_question="문장에서 Tom이 무엇을 놓쳤는지 먼저 찾아볼까요?",
                     hint_keywords=["missed", "so"], hint_text="so 앞부분에 행동의 이유가 있어요.")
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *a: (help_turn.model_dump_json(), "openai"))
    text, feedback, _, meta = tutor.tutor_reply(None, "영어 이해", "모르겠어요", "영어", conversation_history=history())
    assert "Because he missed the bus." not in text
    assert meta["hint"]["keywords"] == ["missed", "so"] and meta["stage"] == "개념 설명"
    assert feedback["assessment"] == "unassessed" and meta["dialogue_state"]["evidence"] == []


def test_missing_source_cannot_check_english_learning(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *a: (turn().model_dump_json(), "openai"))
    _, _, _, meta = tutor.tutor_reply(None, "영어 이해", "Because he missed the bus.", "영어", conversation_history=history())
    assert meta["stage"] == "개념 설명" and meta["dialogue_state"]["evidence"] == []


def test_provider_failure_keeps_practice_and_no_mastery(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *a: (None, "rule"))
    text, _, _, meta = tutor.tutor_reply(None, "영어 이해", "모르겠어요", "영어", conversation_history=history())
    assert "영어 문장" in text and "이해 질문이란" not in text
    assert meta["hint"]["keywords"] != ["뜻", "특징", "예시"]
    assert meta["ai_provider"] == "rule" and meta["dialogue_state"]["evidence"] == []


@pytest.mark.parametrize("answer", ["Can I borrow a pen?", "Could you lend me a pen?", "May I borrow your pen?"])
def test_question_form_english_sentence_is_an_answer_to_writing_task(monkeypatch, answer):
    question = "친구에게 펜을 빌려 달라고 영어 한 문장으로 말해볼까요?"
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [SOURCE])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *a: (turn(assessment="partial", answer_status="partial",
        evidence_quote=answer, next_question_goal="application").model_dump_json(), "openai"))
    text, _, _, meta = tutor.tutor_reply(None, "영어 표현", answer, "영어", conversation_history=history(question))
    assert meta["dialogue_state"]["last_intent"] == "answer"
    assert "영어 문장을 다시 써" in text and "누가 무엇을" not in text
    prior = history(question)
    prior[0]["response_meta"]["practice_mode"] = "english"
    report = learning_report([*prior, {"sender_type": "user", "content": answer}], "영어 표현")
    assert report["first_explanation"] == answer


def test_real_english_questions_are_not_reclassified_as_practice_answers():
    assert not is_question_form_answer("Can you explain this sentence?", "영어 문장으로 말해볼까요?")
    assert not is_question_form_answer("Can I borrow a pen?", "이 표현의 뜻은 무엇인가요?")


def test_english_practice_survives_api_pause_and_resume(client, auth_headers):
    room = client.post("/rooms/personal", headers=auth_headers, json={"subject": "영어", "grade": "중학교 1학년"}).json()["room"]
    created = client.post("/sessions", headers=auth_headers, json={"room_id": room["id"], "topic": "영어 이해",
                         "unit_code": "9영01", "school_level": "중학교", "grade": "1학년"})
    assert created.status_code == 201
    session = created.json()["session"]
    assert "Tom missed" in session["messages"][0]["content"]
    assert session["learning_report"]["checked_count"] == 0
    assert client.post(f"/sessions/{session['id']}/pause", headers=auth_headers).status_code == 200
    resumed = client.post(f"/sessions/{session['id']}/resume", headers=auth_headers).json()["session"]
    assert resumed["messages"] == session["messages"] and resumed["learning_report"]["checked_count"] == 0
