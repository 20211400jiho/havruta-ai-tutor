def test_personal_space_is_reused_private_and_supports_sessions(client, auth_headers):
    payload = {"subject": "수학", "grade": "고등학교 1학년"}
    result = client.post("/rooms/personal", headers=auth_headers, json=payload)
    assert result.status_code == 200
    room_id = result.json()["room"]["id"]
    assert client.post("/rooms/personal", headers=auth_headers, json=payload).json()["room"]["id"] == room_id
    assert client.get("/rooms", headers=auth_headers).json()["rooms"] == []
    room = client.get(f"/rooms/{room_id}", headers=auth_headers).json()["room"]
    assert room["max_members"] == 1
    other = client.post("/auth/signup", json={
        "email": "other-personal@example.com", "password": "strong-password", "name": "다른 학생",
    }).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post("/rooms/join", headers=headers, json={"invite_code": room["invite_code"]}).status_code == 403
    assert client.get(f"/rooms/{room_id}", headers=headers).status_code == 403
    assert client.post("/sessions", headers=headers, json={"room_id": room_id, "topic": "수학"}).status_code == 403
    session = client.post("/sessions", headers=auth_headers, json={"room_id": room_id, "topic": "수학"})
    assert session.status_code == 201
    session_id = session.json()["session"]["id"]
    assert client.get(f"/sessions/{session_id}", headers=auth_headers).status_code == 200
    assert client.get(f"/sessions/{session_id}", headers=headers).status_code == 403
    separate = client.post("/rooms/personal", headers=headers, json=payload)
    assert separate.json()["room"]["id"] != room_id


def test_collaborative_rooms_remain_visible(client, auth_headers):
    response = client.post("/rooms", headers=auth_headers, json={"title": "친구 토론"})
    assert response.status_code == 201
    assert client.get("/rooms", headers=auth_headers).json()["rooms"][0]["id"] == response.json()["room"]["id"]
    assert client.post("/rooms/personal", headers=auth_headers, json={"subject": " ", "grade": "고1"}).status_code == 422
