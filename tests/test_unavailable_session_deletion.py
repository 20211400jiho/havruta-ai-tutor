import pytest

from app.models.ai_feedback import AIFeedback
from app.models.chat import ChatSession, Message
from app.models.document import RagReference
from app.models.learning import LearningRecord, LearningRoom
from app.models.study_content import StudyNote
from conftest import TestSession
from test_session_relearning import create_learning


def close_room(session):
    with TestSession() as db:
        db.get(LearningRoom, session["room_id"]).status = "closed"
        db.commit()


def test_delete_unavailable_session_removes_only_owned_transcript(client, auth_headers):
    old = create_learning(client, auth_headers)
    # Same room, separate transcript must remain intact.
    other = create_learning(client, auth_headers)
    with TestSession() as db:
        message = db.query(Message).filter_by(session_id=old["id"]).first()
        db.add(AIFeedback(session_id=old["id"], message_id=message.id, summary="피드백"))
        db.commit()
    close_room(old)
    summaries = client.get("/sessions", headers=auth_headers).json()["sessions"]
    assert next(s for s in summaries if s["id"] == old["id"])["can_delete"]
    response = client.delete(f"/sessions/{old['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["deleted_session_id"] == old["id"]
    assert client.get(f"/sessions/{old['id']}", headers=auth_headers).status_code == 404
    assert client.get(f"/sessions/{other['id']}", headers=auth_headers).status_code == 200
    assert client.delete(f"/sessions/{old['id']}", headers=auth_headers).status_code == 404
    with TestSession() as db:
        assert not db.query(Message).filter_by(session_id=old["id"]).count()
        assert not db.query(AIFeedback).filter_by(session_id=old["id"]).count()
        assert db.query(Message).filter_by(session_id=other["id"]).count()
        assert not db.query(RagReference).filter(~RagReference.message_id.in_(db.query(Message.id))).count()
        assert db.get(LearningRoom, old["room_id"]) is not None


def test_active_session_cannot_be_deleted(client, auth_headers):
    session = create_learning(client, auth_headers)
    assert not client.get("/sessions", headers=auth_headers).json()["sessions"][0]["can_delete"]
    assert client.delete(f"/sessions/{session['id']}", headers=auth_headers).status_code == 409
    assert client.get(f"/sessions/{session['id']}", headers=auth_headers).status_code == 200


def test_completed_session_note_and_record_are_protected(client, auth_headers):
    session = create_learning(client, auth_headers)
    note = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers).json()["note_id"]
    close_room(session)
    assert client.delete(f"/sessions/{session['id']}", headers=auth_headers).status_code == 409
    with TestSession() as db:
        assert db.get(StudyNote, note) and db.query(LearningRecord).count() == 1
        # Protect saved notes even if legacy data has an inconsistent state.
        db.get(ChatSession, session["id"]).state = "paused"
        db.commit()
    assert client.delete(f"/sessions/{session['id']}", headers=auth_headers).status_code == 409


def test_delete_requires_owner_and_authentication(client, auth_headers):
    session = create_learning(client, auth_headers)
    close_room(session)
    other = client.post("/auth/signup", json={"email": "delete-other@example.com", "password": "strong-password", "name": "다른 학생"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.delete(f"/sessions/{session['id']}", headers=headers).status_code == 403
    assert client.delete(f"/sessions/{session['id']}").status_code in {401, 403}
    assert client.delete("/sessions/999999", headers=auth_headers).status_code == 404


def test_failed_delete_rolls_back_transcript(client, auth_headers, monkeypatch):
    session = create_learning(client, auth_headers)
    close_room(session)
    from sqlalchemy.orm import Session
    def fail_commit(self):
        raise RuntimeError("저장 실패")
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="저장 실패"):
            client.delete(f"/sessions/{session['id']}", headers=auth_headers)
    with TestSession() as db:
        assert db.get(ChatSession, session["id"])
        assert db.query(Message).filter_by(session_id=session["id"]).count()
