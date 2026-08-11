def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_complete_learning_flow(client, auth_headers):
    room_response = client.post(
        "/rooms",
        headers=auth_headers,
        json={
            "title": "고1 수학방",
            "subject": "수학",
            "grade": "고등학교 1학년",
            "max_members": 4,
        },
    )
    assert room_response.status_code == 201
    room = room_response.json()["room"]
    assert len(room["invite_code"]) == 6

    session_response = client.post(
        "/sessions",
        headers=auth_headers,
        json={"room_id": room["id"], "topic": "직선의 방정식"},
    )
    assert session_response.status_code == 201
    session = session_response.json()["session"]
    assert session["messages"][0]["sender_type"] == "ai"

    answer_response = client.post(
        f"/sessions/{session['id']}/messages",
        headers=auth_headers,
        json={"content": "두 점의 x좌표가 같으므로 이 직선은 y축과 평행합니다."},
    )
    assert answer_response.status_code == 200
    assert answer_response.json()["feedback"]["score"] >= 50
    assert answer_response.json()["message"]["sender_type"] == "ai"

    finish_response = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers)
    assert finish_response.status_code == 200
    assert finish_response.json()["note_id"]

    notes_response = client.get("/notes", headers=auth_headers)
    assert notes_response.status_code == 200
    assert notes_response.json()["count"] == 1

    dashboard_response = client.get("/dashboard/me", headers=auth_headers)
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["summary"]["completed_sessions"] == 1


def test_authenticated_room_chat_and_history(client, auth_headers):
    room_response = client.post(
        "/rooms",
        headers=auth_headers,
        json={
            "title": "실시간 토론방",
            "subject": "수학",
            "grade": "고등학교 1학년",
            "max_members": 4,
        },
    )
    room_id = room_response.json()["room"]["id"]
    token = auth_headers["Authorization"].removeprefix("Bearer ")

    with client.websocket_connect(f"/chat/ws/{room_id}") as websocket:
        websocket.send_json({"type": "authenticate", "token": token})
        authenticated = websocket.receive_json()
        assert authenticated["type"] == "authenticated"
        presence = websocket.receive_json()
        assert presence["type"] == "presence"
        assert presence["action"] == "joined"

        websocket.send_json({"content": "두 점의 x좌표가 같으면 어떤 직선인가요?"})
        event = websocket.receive_json()
        assert event["type"] == "message"
        assert event["message"]["content"].startswith("두 점의 x좌표")
        assert event["message"]["user_name"] == "테스트 학생"

    history = client.get(f"/chat/rooms/{room_id}/messages", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()["count"] == 1
    assert history.json()["messages"][0]["content"].startswith("두 점의 x좌표")


def test_rag_search(client, auth_headers):
    response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={"query": "두 점의 x좌표가 같으면 직선은 어떻게 되나요?", "top_k": 3},
    )
    assert response.status_code == 200
    assert response.json()["results"]
    assert "평행" in response.json()["results"][0]["content"]


def test_science_session_returns_renderable_message(client, auth_headers):
    room_response = client.post(
        "/rooms",
        headers=auth_headers,
        json={
            "title": "고1 과학방",
            "subject": "과학",
            "grade": "고등학교 1학년",
            "max_members": 4,
        },
    )
    room_id = room_response.json()["room"]["id"]
    session_response = client.post(
        "/sessions",
        headers=auth_headers,
        json={"room_id": room_id, "topic": "광합성"},
    )
    session_id = session_response.json()["session"]["id"]

    answer_response = client.post(
        f"/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "식물은 빛을 이용해 양분을 만듭니다."},
    )

    assert answer_response.status_code == 200
    assert isinstance(answer_response.json()["message"]["content"], str)
    assert answer_response.json()["message"]["content"]

    rag_response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={"query": "광합성", "subject": "과학", "top_k": 3},
    )
    assert rag_response.status_code == 200
    assert rag_response.json()["results"] == []


def test_generate_and_submit_quiz(client, auth_headers):
    created = client.post(
        "/quizzes",
        headers=auth_headers,
        json={"topic": "직선의 방정식", "question_count": 3},
    )
    assert created.status_code == 201
    quiz_id = created.json()["quiz"]["id"]
    detail = client.get(f"/quizzes/{quiz_id}", headers=auth_headers)
    assert detail.status_code == 200
    question_count = len(detail.json()["quiz"]["questions"])
    submitted = client.post(
        f"/quizzes/{quiz_id}/submit",
        headers=auth_headers,
        json={"answers": [0] * question_count},
    )
    assert submitted.status_code == 200
    assert 0 <= submitted.json()["score"] <= 100
