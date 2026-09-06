import pytest
from starlette.websockets import WebSocketDisconnect


def test_owner_deletes_room_and_preserves_learning(client, auth_headers):
    room = client.post("/rooms", headers=auth_headers, json={
        "title": "삭제할 방", "subject": "수학", "grade": "고등학교 1학년", "max_members": 4,
    }).json()["room"]
    other = client.post("/auth/signup", json={
        "email": "member@example.com", "password": "strong-password", "name": "참여자",
    }).json()
    member_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post("/rooms/join", headers=member_headers, json={"invite_code": room["invite_code"]}).status_code == 200
    session = client.post("/sessions", headers=auth_headers, json={
        "room_id": room["id"], "topic": "도형의 방정식", "unit_code": "10공수2-01",
    }).json()["session"]
    finished = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers)
    assert finished.status_code == 200

    url = f"/rooms/{room['id']}"
    assert client.delete(url, headers=member_headers).status_code == 403
    assert client.get(url, headers=auth_headers).status_code == 200
    assert client.delete(url, headers=auth_headers).status_code == 200
    assert client.delete(url, headers=auth_headers).status_code == 200
    for headers in (auth_headers, member_headers):
        assert client.get("/rooms", headers=headers).json()["rooms"] == []
        assert client.get(url, headers=headers).status_code == 404
        assert client.post("/rooms/join", headers=headers, json={"invite_code": room["invite_code"]}).status_code == 409
        assert client.get(f"/chat/rooms/{room['id']}/messages", headers=headers).status_code == 403
    assert client.post("/sessions", headers=auth_headers, json={
        "room_id": room["id"], "topic": "도형의 방정식", "unit_code": "10공수2-01",
    }).status_code == 409
    assert client.get(f"/sessions/{session['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/notes/{finished.json()['note_id']}", headers=auth_headers).status_code == 200
    assert client.delete("/rooms/999999", headers=auth_headers).status_code == 404


def test_deleted_room_blocks_existing_websocket(client, auth_headers):
    room = client.post("/rooms", headers=auth_headers, json={
        "title": "채팅 삭제", "subject": "수학", "grade": "고등학교 1학년",
    }).json()["room"]
    with client.websocket_connect(f"/chat/ws/{room['id']}") as socket:
        socket.send_json({"type": "authenticate", "token": auth_headers["Authorization"].split()[1]})
        assert socket.receive_json()["type"] == "authenticated"
        assert socket.receive_json()["type"] == "presence"
        assert client.delete(f"/rooms/{room['id']}", headers=auth_headers).status_code == 200
        assert socket.receive_json()["type"] == "room_deleted"
        socket.send_json({"content": "삭제 이후 전송"})
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 4403
