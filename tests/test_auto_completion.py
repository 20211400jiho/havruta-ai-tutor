import pytest

from app.models.chat import ChatSession, Message
from app.models.learning import LearningRecord
from app.models.study_content import StudyNote
from app.rag import tutor
from app.rag.dialogue import DialogueState, ProgressiveTutorTurn, STAGES
from conftest import TestSession
from test_session_relearning import create_learning

ANSWER = "계수의 부호에 따라 변화 방향이 달라지므로, 조건을 확인하고 새 문제에 적용해야 합니다."


def seed(client, headers, count=4):
    session = create_learning(client, headers)
    state = DialogueState(stage=STAGES[min(count, 4)], focus_question="오늘 배운 핵심을 정리해볼까요?",
                          last_question="오늘 배운 핵심을 정리해볼까요?", learning_goal="함수의 변화 방향 설명",
                          evidence=[{"stage":name,"quote":f"{name} 설명","source_ids":["m1"]} for name in STAGES[:count]])
    with TestSession() as db:
        db.add(Message(session_id=session["id"],sender_type="ai",content=state.last_question,
                       response_meta_json={"dialogue_state":state.model_dump()}))
        db.commit()
    return session


def model(monkeypatch, **changes):
    monkeypatch.setattr(tutor, "search", lambda *a, **k: [tutor.SearchResult(None,"m1","함수는 계수의 부호에 따라 변화 방향이 달라집니다.",.9,{})])
    values=dict(explanation="배운 핵심을 정리했어요.",next_question="새 문제를 더 풀어볼까요?",next_question_goal="review",
                assessment="understood",answer_status="correct",evidence_quote=ANSWER,source_ids=["m1"],reasoning="핵심을 정리했습니다.",misconception="")
    monkeypatch.setattr(tutor,"generate_with_provider",lambda *a:(ProgressiveTutorTurn(**{**values,**changes}).model_dump_json(),"openai"))


def test_final_message_saves_record_and_note_atomically_and_closes_chat(client, auth_headers, monkeypatch):
    session=seed(client,auth_headers)
    model(monkeypatch)
    result=client.post(f"/sessions/{session['id']}/messages",headers=auth_headers,json={"content":ANSWER})
    assert result.status_code == 200
    data=result.json()
    assert data["session_state"] == "finished" and data["completion"]["goals_completed"]
    assert data["learning_report"]["checked_count"] == 5
    assert "새 문제를 더 풀어" not in data["message"]["content"]
    assert data["feedback"]["followup_question"] == ""
    note_id=data["completion"]["note_id"]
    with TestSession() as db:
        assert db.get(ChatSession,session["id"]).state == "finished"
        assert db.query(LearningRecord).count() == db.query(StudyNote).count() == 1
        assert ANSWER in db.get(StudyNote,note_id).content
    repeat=client.post(f"/sessions/{session['id']}/finish",headers=auth_headers).json()
    assert repeat["note_id"] == note_id and repeat["learning_report"] == data["learning_report"]
    assert client.post(f"/sessions/{session['id']}/messages",headers=auth_headers,json={"content":ANSWER}).status_code == 409
    assert client.post(f"/sessions/{session['id']}/resume",headers=auth_headers).status_code == 409
    with TestSession() as db:
        assert db.query(LearningRecord).count() == db.query(StudyNote).count() == 1


@pytest.mark.parametrize("case", ["partial","source","quote","help"])
def test_four_checks_do_not_finish_without_valid_final_evidence(client,auth_headers,monkeypatch,case):
    session=seed(client,auth_headers)
    changes={"assessment":"partial","answer_status":"partial"} if case=="partial" else {"source_ids":["invented"]} if case=="source" else {"evidence_quote":"학생이 답하지 않은 문장"} if case=="quote" else {}
    model(monkeypatch,**changes)
    payload={"content":ANSWER,**({"help_action":"hint"} if case=="help" else {})}
    data=client.post(f"/sessions/{session['id']}/messages",headers=auth_headers,json=payload).json()
    assert data["completion"] is None and data["session_state"] != "finished"
    assert data["learning_report"]["checked_count"] == 4
    assert "마지막 정리" in data["learning_report"]["progress_message"]
    with TestSession() as db:
        assert db.query(LearningRecord).count() == db.query(StudyNote).count() == 0


def test_note_failure_rolls_back_final_answer_and_completion(client,auth_headers,monkeypatch):
    from app.routers import sessions
    session=seed(client,auth_headers)
    model(monkeypatch)
    with TestSession() as db:
        before=db.query(Message).filter_by(session_id=session["id"]).count()
    def fail(*args): raise RuntimeError("노트 저장 실패")
    monkeypatch.setattr(sessions,"create_note_for_session",fail)
    with pytest.raises(RuntimeError,match="노트 저장 실패"):
        client.post(f"/sessions/{session['id']}/messages",headers=auth_headers,json={"content":ANSWER})
    with TestSession() as db:
        assert db.query(Message).filter_by(session_id=session["id"]).count() == before
        assert db.query(LearningRecord).count() == db.query(StudyNote).count() == 0
        assert db.get(ChatSession,session["id"]).state != "finished"


def test_legacy_five_checked_session_finalizes_on_resume(client,auth_headers):
    session=seed(client,auth_headers,5)
    result=client.post(f"/sessions/{session['id']}/resume",headers=auth_headers)
    assert result.status_code == 200
    data=result.json()
    assert data["session"]["state"] == "finished" and data["completion"]["goals_completed"]
    assert data["completion"]["note_id"]


def test_manual_early_finish_preserves_incomplete_status(client,auth_headers):
    session=seed(client,auth_headers,2)
    data=client.post(f"/sessions/{session['id']}/finish",headers=auth_headers).json()
    assert not data["goals_completed"] and data["learning_report"]["checked_count"] == 2
    assert data["note_id"]
