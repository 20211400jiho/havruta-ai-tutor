from datetime import datetime

from app.database.config import settings
from app.rag import retriever as rag_service


def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["database"]["ready"] is True
    assert readiness.json()["rag"]["provider"] == "lexical"
    assert readiness.json()["ai"]["rule_fallback_ready"] is True


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
        json={
            "room_id": room["id"],
            "topic": "도형의 방정식",
            "unit_code": "10공수2-01",
        },
    )
    assert session_response.status_code == 201
    session = session_response.json()["session"]
    assert session["unit_code"] == "10공수2-01"
    assert session["school_level"] == "고등학교"
    assert session["grade"] == "1학년"
    assert session["messages"][0]["sender_type"] == "ai"

    answer_response = client.post(
        f"/sessions/{session['id']}/messages",
        headers=auth_headers,
        json={"content": "두 점의 x좌표가 같으므로 이 직선은 y축과 평행합니다."},
    )
    assert answer_response.status_code == 200
    answer_payload = answer_response.json()
    assert answer_payload["feedback"]["score"] is None
    assert answer_payload["feedback"]["assessment"] == "unassessed"
    assert answer_payload["learning_report"]["checked_count"] == 0
    assert answer_payload["message"]["sender_type"] == "ai"
    assert answer_payload["response_meta"]["ai_provider"] == "rule"
    assert answer_payload["response_meta"]["retriever"] == "lexical"
    # Rule fallback cannot establish understanding, even for a long answer.
    assert answer_payload["response_meta"]["stage"] == "개념 설명"
    assert answer_payload["response_meta"]["sources"]

    restored_response = client.get(f"/sessions/{session['id']}", headers=auth_headers)
    assert restored_response.status_code == 200
    restored_ai = restored_response.json()["session"]["messages"][-1]
    assert restored_ai["sender_type"] == "ai"
    assert restored_ai["response_meta"]["sources"]
    assert restored_response.json()["response_meta"]["stage"] == "개념 설명"

    finish_response = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers)
    assert finish_response.status_code == 200
    assert finish_response.json()["note_id"]

    notes_response = client.get("/notes", headers=auth_headers)
    assert notes_response.status_code == 200
    assert notes_response.json()["count"] == 1
    note_detail = client.get(f"/notes/{finish_response.json()['note_id']}", headers=auth_headers)
    section_titles = [section["title"] for section in note_detail.json()["note"]["sections"]]
    assert "핵심 개념과 나의 설명" in section_titles
    assert "보완할 개념" in section_titles
    assert "2022 교육과정 근거" in section_titles

    dashboard_response = client.get("/dashboard/me", headers=auth_headers)
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["summary"]["completed_sessions"] == 1
    assert dashboard_response.json()["summary"]["completed_units"] == 1
    now = datetime.now()
    calendar_response = client.get(
        f"/dashboard/calendar?year={now.year}&month={now.month}",
        headers=auth_headers,
    )
    assert calendar_response.status_code == 200
    calendar_events = calendar_response.json()["events"]
    assert sum(len(event["notes"]) for event in calendar_events) == 1


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


def test_collaborative_havruta_compares_two_students(client, auth_headers):
    room_response = client.post(
        "/rooms",
        headers=auth_headers,
        json={"title": "공동 하브루타", "subject": "수학", "grade": "고등학교 1학년", "max_members": 4},
    )
    room = room_response.json()["room"]
    second_signup = client.post(
        "/auth/signup",
        json={
            "email": "partner@example.com",
            "password": "strong-password",
            "name": "토론 파트너",
            "grade": "고등학교 1학년",
        },
    )
    second_token = second_signup.json()["access_token"]
    second_headers = {"Authorization": f"Bearer {second_token}"}
    joined = client.post("/rooms/join", headers=second_headers, json={"invite_code": room["invite_code"]})
    assert joined.status_code == 200

    first_token = auth_headers["Authorization"].removeprefix("Bearer ")
    for token, content in (
        (first_token, "두 점의 x좌표가 같으면 직선은 y축과 평행합니다."),
        (second_token, "기울기를 정의할 수 없다는 점도 함께 확인해야 합니다."),
    ):
        with client.websocket_connect(f"/chat/ws/{room['id']}") as websocket:
            websocket.send_json({"type": "authenticate", "token": token})
            assert websocket.receive_json()["type"] == "authenticated"
            assert websocket.receive_json()["type"] == "presence"
            websocket.send_json({"content": content})
            assert websocket.receive_json()["type"] == "message"

    result = client.post(
        f"/chat/rooms/{room['id']}/ai-feedback",
        headers=auth_headers,
        json={
            "topic": "직선의 방정식",
            "unit_code": "10공수2-01",
            "school_level": "고등학교",
            "grade": "1학년",
        },
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["participant_count"] == 2
    assert len(payload["participant_views"]) == 2
    assert payload["response_meta"]["ai_provider"] == "rule"
    assert payload["response_meta"]["grounded"] is True


def test_rag_search(client, auth_headers):
    response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={"query": "두 점의 x좌표가 같으면 직선은 어떻게 되나요?", "top_k": 3},
    )
    assert response.status_code == 200
    assert response.json()["curriculum_year"] == "2022"
    assert response.json()["alignment_policy"] == "source_or_achievement_standard"
    assert response.json()["results"]
    assert "평행" in response.json()["results"][0]["content"]
    assert all(
        result["metadata"]["rag_curriculum_year"] == "2022"
        and result["metadata"]["curriculum_alignment"] in {"source", "achievement_standard"}
        and result["metadata"].get("achievement_standard_2022")
        for result in response.json()["results"]
    )

    math_status = client.get("/rag/status?subject=수학", headers=auth_headers)
    science_status = client.get("/rag/status?subject=과학", headers=auth_headers)
    assert math_status.json()["available"] is True
    assert math_status.json()["curriculum_year"] == "2022"
    assert science_status.json()["available"] is False


def test_rag_auto_provider_falls_back_to_lexical(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "rag_provider", "auto")
    monkeypatch.setattr(rag_service, "search_chroma", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced")))
    response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={"query": "두 점의 x좌표가 같은 직선", "subject": "수학", "top_k": 1},
    )
    assert response.status_code == 200
    assert response.json()["results"]
    assert response.json()["results"][0]["metadata"]["retriever"] == "lexical"


def test_curriculum_catalog_and_selected_standard_filter(client, auth_headers):
    catalog_response = client.get("/rag/catalog?subject=수학", headers=auth_headers)
    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert catalog["curriculum_year"] == "2022"
    assert catalog["name"] == "수학"
    assert catalog["standard_count"] > 0
    high_school = next(level for level in catalog["school_levels"] if level["name"] == "고등학교")
    first_grade = next(grade for grade in high_school["grades"] if grade["name"] == "1학년")
    geometry = next(unit for unit in first_grade["units"] if unit["code"] == "10공수2-01")
    assert geometry["title"] == "도형의 방정식"
    assert any(item["code"] == "10공수2-01-02" for item in geometry["standards"])

    selected_response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={
            "query": "도형의 방정식 · [10공수2-01-02] 두 직선의 평행 조건과 수직 조건",
            "subject": "수학",
            "top_k": 3,
        },
    )
    assert selected_response.status_code == 200
    assert selected_response.json()["results"]
    assert all(
        "[10공수2-01-02]" in result["metadata"]["achievement_standard_2022"]
        for result in selected_response.json()["results"]
    )

    missing_response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={"query": "[10공수2-99-99] 존재하지 않는 성취기준", "subject": "수학"},
    )
    assert missing_response.status_code == 200
    assert missing_response.json()["results"] == []

    unit_response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={
            "query": "도형의 방정식",
            "subject": "수학",
            "unit_code": "10공수2-01",
            "school_level": "고등학교",
            "grade": "1학년",
            "top_k": 3,
        },
    )
    assert unit_response.status_code == 200
    assert unit_response.json()["results"]
    assert all(
        "[10공수2-01-" in result["metadata"]["achievement_standard_2022"]
        and result["metadata"]["selected_unit_code"] == "10공수2-01"
        for result in unit_response.json()["results"]
    )


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
        json={
            "subject": "수학",
            "topic": "도형의 방정식",
            "unit_code": "10공수2-01",
            "school_level": "고등학교",
            "grade": "1학년",
            "question_count": 3,
        },
    )
    assert created.status_code == 201
    quiz_id = created.json()["quiz"]["id"]
    detail = client.get(f"/quizzes/{quiz_id}", headers=auth_headers)
    assert detail.status_code == 200
    question_count = len(detail.json()["quiz"]["questions"])
    assert all(len(question["options"]) == 4 for question in detail.json()["quiz"]["questions"])
    assert all(len(set(question["options"])) == 4 for question in detail.json()["quiz"]["questions"])
    submitted = client.post(
        f"/quizzes/{quiz_id}/submit",
        headers=auth_headers,
        json={"answers": [0] * question_count},
    )
    assert submitted.status_code == 200
    assert 0 <= submitted.json()["score"] <= 100


def test_quiz_does_not_fall_back_to_unrelated_subject(client, auth_headers):
    created = client.post(
        "/quizzes",
        headers=auth_headers,
        json={"subject": "과학", "topic": "광합성", "question_count": 3},
    )
    assert created.status_code == 422
    assert "RAG" in created.json()["detail"]
    assert client.get("/quizzes", headers=auth_headers).json()["count"] == 0


def test_public_signup_cannot_assign_teacher_role(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "teacher@example.com",
            "password": "strong-password",
            "name": "교사 권한 요청",
            "grade": None,
            "role": "teacher",
        },
    )
    assert response.status_code == 422


def test_uncertain_answer_resumes_without_advancing_stage(client, auth_headers):
    room = client.post(
        "/rooms",
        headers=auth_headers,
        json={"title": "대화 연속성", "subject": "영어", "grade": "고등학교 1학년"},
    ).json()["room"]
    session = client.post(
        "/sessions",
        headers=auth_headers,
        json={"room_id": room["id"], "topic": "용이한 표현"},
    ).json()["session"]

    uncertain = client.post(
        f"/sessions/{session['id']}/messages",
        headers=auth_headers,
        json={"content": "몰라"},
    )
    assert uncertain.status_code == 200
    assert uncertain.json()["feedback"]["score"] is None
    assert uncertain.json()["response_meta"]["stage"] == "개념 설명"

    restored = client.get(f"/sessions/{session['id']}", headers=auth_headers)
    assert restored.status_code == 200
    assert [item["sender_type"] for item in restored.json()["session"]["messages"]] == [
        "ai",
        "user",
        "ai",
    ]
    assert restored.json()["response_meta"]["stage"] == "개념 설명"

    substantive = client.post(
        f"/sessions/{session['id']}/messages",
        headers=auth_headers,
        json={"content": "useful은 도움에 가깝고 convenient는 사용하기 편한 상황 같아요."},
    )
    assert substantive.status_code == 200
    assert substantive.json()["response_meta"]["stage"] == "개념 설명"


def test_invalid_grade_unit_combination_is_rejected(client, auth_headers):
    response = client.post(
        "/rag/search",
        headers=auth_headers,
        json={
            "query": "도형의 방정식",
            "subject": "수학",
            "school_level": "중학교",
            "grade": "1학년",
            "unit_code": "10공수2-01",
        },
    )
    assert response.status_code == 422
    assert "조합" in response.json()["detail"]


def test_ai_request_rate_limit_returns_retry_after(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "ai_requests_per_minute", 1)
    room = client.post(
        "/rooms",
        headers=auth_headers,
        json={"title": "사용량 제한", "subject": "수학", "grade": "고등학교 1학년"},
    ).json()["room"]
    session = client.post(
        "/sessions",
        headers=auth_headers,
        json={"room_id": room["id"], "topic": "수학 설명"},
    ).json()["session"]
    first = client.post(
        f"/sessions/{session['id']}/messages",
        headers=auth_headers,
        json={"content": "좌표를 이용해 설명해볼게요."},
    )
    assert first.status_code == 200

    limited = client.post(
        f"/sessions/{session['id']}/messages",
        headers=auth_headers,
        json={"content": "한 번 더 설명할게요."},
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
