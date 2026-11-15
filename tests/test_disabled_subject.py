from app.rag import curriculum


def test_disabled_subject_is_not_offered(client, auth_headers):
    assert client.get("/rag/catalog", params={"subject": "영어"}, headers=auth_headers).status_code == 404
    assert client.get("/rag/catalog", params={"subject": "수학"}, headers=auth_headers).status_code == 200
    assert client.post("/rooms", headers=auth_headers,
                       json={"title": "영어방", "subject": "영어", "grade": "고등학교 1학년"}).status_code == 422
    assert client.post("/rooms/personal", headers=auth_headers,
                       json={"subject": "영어", "grade": "고등학교 1학년"}).status_code == 422
    assert client.post("/quizzes", headers=auth_headers,
                       json={"topic": "영어 이해", "subject": "영어", "question_count": 3}).status_code == 422


def test_session_of_withdrawn_subject_can_be_deleted_but_not_resumed(client, auth_headers, monkeypatch):
    monkeypatch.setattr(curriculum, "DISABLED_SUBJECTS", frozenset())
    english_room = client.post("/rooms/personal", headers=auth_headers,
                               json={"subject": "영어", "grade": "고등학교 1학년"}).json()["room"]
    math_room = client.post("/rooms/personal", headers=auth_headers,
                            json={"subject": "수학", "grade": "고등학교 1학년"}).json()["room"]
    english = client.post("/sessions", headers=auth_headers,
                          json={"room_id": english_room["id"], "topic": "영어 이해"}).json()["session"]
    math = client.post("/sessions", headers=auth_headers,
                       json={"room_id": math_room["id"], "topic": "도형의 방정식"}).json()["session"]

    # The subject is withdrawn after the learner already started it.
    monkeypatch.setattr(curriculum, "DISABLED_SUBJECTS", frozenset({"영어"}))
    summaries = {s["id"]: s for s in client.get("/sessions", headers=auth_headers).json()["sessions"]}
    assert summaries[english["id"]]["can_delete"] and not summaries[english["id"]]["can_resume"]
    assert summaries[math["id"]]["can_resume"] and not summaries[math["id"]]["can_delete"]
    assert client.post(f"/sessions/{english['id']}/resume", headers=auth_headers).status_code == 409
    assert client.post("/sessions", headers=auth_headers,
                       json={"room_id": english_room["id"], "topic": "영어 이해"}).status_code == 409

    assert client.delete(f"/sessions/{english['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/sessions/{english['id']}", headers=auth_headers).status_code == 404
    # Sessions of offered subjects keep the existing protection.
    assert client.delete(f"/sessions/{math['id']}", headers=auth_headers).status_code == 409
