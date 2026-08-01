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


def test_rag_search(client, auth_headers):
    response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={"query": "두 점의 x좌표가 같으면 직선은 어떻게 되나요?", "top_k": 3},
    )
    assert response.status_code == 200
    assert response.json()["results"]
    assert "평행" in response.json()["results"][0]["content"]


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
