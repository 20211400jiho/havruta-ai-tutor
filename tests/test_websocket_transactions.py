from app.database.connection import get_db
from conftest import TestSession
from main import app
from scripts.migrate_schema import invite_code_is_nullable


def test_room_websocket_holds_no_transaction_while_waiting(client, auth_headers):
    room_id = client.post("/rooms", headers=auth_headers, json={
        "title": "토론", "subject": "사회", "grade": "고등학교 1학년", "max_members": 4,
    }).json()["room"]["id"]
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    sessions = []

    def tracked_db():
        db = TestSession()
        sessions.append(db)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = tracked_db
    with client.websocket_connect(f"/chat/ws/{room_id}") as websocket:
        websocket.send_json({"type": "authenticate", "token": token})
        assert websocket.receive_json()["type"] == "authenticated"
        # An idle open transaction here blocked a deploy's ALTER TABLE and every
        # later learning_rooms query on 2026-11-17.
        assert not sessions[-1].in_transaction()
        assert websocket.receive_json()["type"] == "presence"
        websocket.send_json({"content": "시민 참여가 필요해"})
        event = websocket.receive_json()
        assert event["type"] == "message" and event["message"]["user_name"] == "테스트 학생"
        assert not sessions[-1].in_transaction()


def test_invite_code_column_change_runs_only_while_nullable():
    assert invite_code_is_nullable([{"name": "id", "nullable": False}, {"name": "invite_code", "nullable": True}])
    assert not invite_code_is_nullable([{"name": "invite_code", "nullable": False}])
