import pytest

from app.models.chat import ChatSession, Message
from app.models.learning import LearningRecord
from app.models.study_content import StudyNote
from app.rag.dialogue import DialogueState
from conftest import TestSession


def create_learning(client, headers):
    room = client.post("/rooms/personal", headers=headers, json={"subject": "수학", "grade": "고등학교 1학년"}).json()["room"]
    response = client.post("/sessions", headers=headers, json={
        "room_id": room["id"], "topic": "도형의 방정식", "unit_code": "10공수2-01",
        "school_level": "고등학교", "grade": "1학년",
    })
    assert response.status_code == 201
    return response.json()["session"]


def add_progress(session_id):
    state = DialogueState(stage="생각 수정", focus_question="다른 경우에도 성립할까요?", last_question="다른 경우에도 성립할까요?",
                          scaffold_count=2, last_hint_keywords=["조건"], evidence=[
                              {"stage": "개념 설명", "quote": "x좌표가 같습니다.", "source_ids": ["math-1"]},
                              {"stage": "근거 확인", "quote": "x좌표가 같기 때문입니다.", "source_ids": ["math-1"]},
                          ])
    with TestSession() as db:
        db.add_all([
            Message(session_id=session_id, sender_type="user", content="x좌표가 같기 때문입니다."),
            Message(session_id=session_id, sender_type="ai", content="다른 경우에도 성립할까요?", response_meta_json={
                "dialogue_state": state.model_dump(), "hint": {"level": 2, "keywords": ["조건"]},
            }),
        ])
        db.commit()
    return state


def test_pause_list_and_resume_preserve_messages_progress_and_hint_state(client, auth_headers):
    session = create_learning(client, auth_headers)
    state = add_progress(session["id"])
    before = client.get(f"/sessions/{session['id']}", headers=auth_headers).json()["session"]
    for _ in range(2):
        paused = client.post(f"/sessions/{session['id']}/pause", headers=auth_headers)
        assert paused.status_code == 200 and paused.json()["session"]["state"] == "paused"
    summary = client.get("/sessions", headers=auth_headers).json()["sessions"][0]
    assert summary["checked_count"] == 2 and summary["total_count"] == 5
    assert summary["stage"] == "생각 수정" and summary["answer_count"] == 1
    assert summary["last_question"] == state.last_question and summary["last_activity_at"]
    assert summary["subject"] == "수학" and summary["can_resume"] and "messages" not in summary
    resumed = client.post(f"/sessions/{session['id']}/resume", headers=auth_headers).json()
    assert resumed["session"]["id"] == session["id"]
    assert resumed["session"]["messages"] == before["messages"]
    assert resumed["response_meta"]["dialogue_state"] == state.model_dump()
    assert resumed["session"]["learning_report"]["checked_count"] == 2
    with TestSession() as db:
        assert db.query(LearningRecord).count() == db.query(StudyNote).count() == 0


def test_restart_copies_scope_but_resets_learning_without_deleting_old_history(client, auth_headers):
    previous = create_learning(client, auth_headers)
    state = add_progress(previous["id"])
    before = client.get(f"/sessions/{previous['id']}", headers=auth_headers).json()["session"]
    response = client.post(f"/sessions/{previous['id']}/restart", headers=auth_headers)
    assert response.status_code == 201
    fresh = response.json()["session"]
    assert fresh["id"] != previous["id"] and response.json()["restarted_from_session_id"] == previous["id"]
    for field in ["room_id", "user_id", "topic", "unit_code", "school_level", "grade", "subject"]:
        assert fresh[field] == previous[field]
    assert fresh["learning_report"]["checked_count"] == 0 and fresh["stage"] == "개념 설명"
    assert fresh["messages"][0]["response_meta"]["dialogue_state"]["scaffold_count"] == 0
    assert len(fresh["messages"]) == 1 and fresh["answer_count"] == 0
    old = client.get(f"/sessions/{previous['id']}", headers=auth_headers).json()["session"]
    assert old["state"] == "paused" and old["messages"] == before["messages"]
    assert old["learning_report"]["checked_count"] == len(state.evidence)
    assert client.get("/sessions", headers=auth_headers).json()["count"] == 2
    with TestSession() as db:
        assert db.query(LearningRecord).count() == db.query(StudyNote).count() == 0


def test_finished_learning_can_restart_but_cannot_resume_or_pause(client, auth_headers):
    previous = create_learning(client, auth_headers)
    finished = client.post(f"/sessions/{previous['id']}/finish", headers=auth_headers).json()
    for action in ["resume", "pause"]:
        assert client.post(f"/sessions/{previous['id']}/{action}", headers=auth_headers).status_code == 409
    assert client.post(f"/sessions/{previous['id']}/restart", headers=auth_headers).status_code == 201
    with TestSession() as db:
        assert db.get(ChatSession, previous["id"]).state == "finished"
        assert db.get(StudyNote, finished["note_id"])
        assert db.query(LearningRecord).count() == 1


@pytest.mark.parametrize("action", ["pause", "resume", "restart"])
def test_other_users_cannot_change_or_copy_learning(client, auth_headers, action):
    previous = create_learning(client, auth_headers)
    other = client.post("/auth/signup", json={"email": "session-other@example.com", "password": "strong-password", "name": "다른 학생"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post(f"/sessions/{previous['id']}/{action}", headers=headers).status_code == 403
    assert client.get("/sessions", headers=headers).json()["sessions"] == []
    assert client.post(f"/sessions/999999/{action}", headers=auth_headers).status_code == 404
    assert client.post(f"/sessions/{previous['id']}/{action}").status_code in {401, 403}


def test_deleted_room_blocks_resume_and_restart_but_keeps_transcript(client, auth_headers):
    room = client.post("/rooms", headers=auth_headers, json={"title": "삭제할 학습방", "subject": "수학", "grade": "고등학교 1학년"}).json()["room"]
    previous = client.post("/sessions", headers=auth_headers, json={"room_id": room["id"], "topic": "수학"}).json()["session"]
    client.delete(f"/rooms/{room['id']}", headers=auth_headers)
    for action in ["resume", "restart"]:
        assert client.post(f"/sessions/{previous['id']}/{action}", headers=auth_headers).status_code == 409
    assert client.get(f"/sessions/{previous['id']}", headers=auth_headers).status_code == 200
    summary = client.get("/sessions", headers=auth_headers).json()["sessions"][0]
    assert not summary["can_resume"] and not summary["can_restart"]
    with TestSession() as db:
        assert db.query(ChatSession).count() == 1


def test_legacy_session_without_snapshot_is_listed_as_unconfirmed(client, auth_headers):
    previous = create_learning(client, auth_headers)
    with TestSession() as db:
        for message in db.query(Message).filter_by(session_id=previous["id"]):
            message.response_meta_json = None
        db.commit()
    summary = client.get("/sessions", headers=auth_headers).json()["sessions"][0]
    assert summary["checked_count"] == 0 and summary["stage"] == "개념 설명"
    assert summary["last_question"]


def test_failed_restart_rolls_back_new_session_and_preserves_original_state(client, auth_headers, monkeypatch):
    from app.routers import sessions
    previous = create_learning(client, auth_headers)
    add_progress(previous["id"])
    def fail(*args, **kwargs):
        raise RuntimeError("검색 서비스 일시 오류")
    monkeypatch.setattr(sessions, "initial_question", fail)
    with pytest.raises(RuntimeError, match="일시 오류"):
        client.post(f"/sessions/{previous['id']}/restart", headers=auth_headers)
    with TestSession() as db:
        assert db.query(ChatSession).count() == 1
        assert db.get(ChatSession, previous["id"]).state == previous["state"]
        assert db.query(Message).filter_by(session_id=previous["id"]).count() == 3
