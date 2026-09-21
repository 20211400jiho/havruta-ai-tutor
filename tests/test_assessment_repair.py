import pytest

from app.rag import tutor
from app.rag.dialogue import ProgressiveTutorTurn, prepare_state, apply_assessment, learning_report
from app.rag.retriever import SearchResult


ANSWER = "쓰레기가 동물을 다치게 하고 흙과 물을 오염시키기 때문이야."


def turn(**changes):
    values = dict(explanation="다른 생명에 미치는 영향을 설명했어요.",
                  next_question="그 이유를 다른 사례와 연결해 설명해볼까요?",
                  assessment="understood", evidence_quote=ANSWER, reasoning="자연 보호의 의미를 설명함",
                  misconception="", source_ids=["source-1"], next_question_goal="reason")
    return ProgressiveTutorTurn(**{**values, **changes})


@pytest.mark.parametrize("answer", [
    "환경을 보호하기 때문 아닌가요?",
    "쓰레기가 동물을 다치게 하기 때문이라고 생각하는데 맞나요?",
])
def test_tentative_explanation_can_be_assessed(answer):
    state = prepare_state([], "자연", answer)
    apply_assessment(state, turn(evidence_quote=answer), answer, {"source-1"})
    assert state.stage == "근거 확인"
    assert len(state.evidence) == 1


def test_whitespace_is_normalized_but_paraphrases_are_not():
    state = prepare_state([], "자연", "다른 생명을\n보호해요.")
    apply_assessment(state, turn(evidence_quote="다른 생명을 보호해요."), "다른 생명을\n보호해요.", {"source-1"})
    assert state.stage == "근거 확인"
    state = prepare_state([], "자연", "보호하지 않아요")
    apply_assessment(state, turn(evidence_quote="보호해요"), "보호하지 않아요", {"source-1"})
    assert state.assessment_issue == "quote_validation"
    assert not state.evidence


@pytest.mark.parametrize("repair_ok", [True, False])
def test_retry_once_and_report_reason(monkeypatch, repair_ok):
    context = SearchResult(None, "source-1", "자연을 보호하고 다른 생명을 존중한다.", .9, {"retriever": "chroma"})
    monkeypatch.setattr(tutor, "search", lambda *args, **kwargs: [context])
    calls = []
    def generate(*args):
        calls.append(args)
        sources = ["source-1"] if len(calls) == 2 and repair_ok else ["invented"]
        return turn(source_ids=sources).model_dump_json(), "openai"
    monkeypatch.setattr(tutor, "generate_with_provider", generate)
    reply, _, _, meta = tutor.tutor_reply(None, "자연", ANSWER)
    report = learning_report([{"sender_type": "ai", "response_meta": meta}], "자연")
    assert len(calls) == 2
    assert 0 < calls[1][-1] <= 15
    assert report["checked_count"] == (1 if repair_ok else 0)
    assert meta["stage"] == ("근거 확인" if repair_ok else "개념 설명")
    if not repair_ok:
        assert report["assessment_issue"] == "source_validation"
        assert "오답이라는 뜻은 아니" in reply


def test_provider_failure_is_not_student_failure(monkeypatch):
    monkeypatch.setattr(tutor, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor, "generate_with_provider", lambda *args: (None, "rule"))
    _, _, _, meta = tutor.tutor_reply(None, "자연", ANSWER)
    assert meta["dialogue_state"]["assessment_issue"] == "provider_unavailable"
    assert not meta["dialogue_state"]["evidence"]
