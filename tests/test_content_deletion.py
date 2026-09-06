import pytest

from conftest import TestSession
from app.models.study_content import QuizQuestion, QuizAttempt


@pytest.mark.parametrize("kind", ["notes", "quizzes"])
def test_content_deletion_checks_owner_and_related_records(client, auth_headers, kind):
    if kind == "notes":
        room = client.post("/rooms", headers=auth_headers, json={
            "title": "노트 삭제 테스트", "subject": "수학", "grade": "고등학교 1학년",
        }).json()["room"]
        session = client.post("/sessions", headers=auth_headers, json={
            "room_id": room["id"], "topic": "도형의 방정식", "unit_code": "10공수2-01",
        }).json()["session"]
        completed = client.post(f"/sessions/{session['id']}/finish", headers=auth_headers)
        assert completed.status_code == 200
        item_id = completed.json()["note_id"]
    else:
        created = client.post("/quizzes", headers=auth_headers, json={
            "subject": "수학", "topic": "도형의 방정식", "unit_code": "10공수2-01",
            "school_level": "고등학교", "grade": "1학년", "question_count": 3,
        })
        assert created.status_code == 201
        item_id = created.json()["quiz"]["id"]
        questions = client.get(f"/quizzes/{item_id}", headers=auth_headers).json()["quiz"]["questions"]
        assert client.post(f"/quizzes/{item_id}/submit", headers=auth_headers, json={
            "answers": [0] * len(questions),
        }).status_code == 200
        with TestSession() as db:
            assert db.query(QuizAttempt).filter_by(quiz_id=item_id).count() == 1

    other = client.post("/auth/signup", json={
        "email": "other-content@example.com", "password": "strong-password", "name": "다른 학생",
    }).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    url = f"/{kind}/{item_id}"
    assert client.delete(url).status_code in (401, 403)
    assert client.delete(url, headers=other_headers).status_code == 403
    assert client.get(url, headers=auth_headers).status_code == 200
    assert client.delete(url, headers=auth_headers).status_code == 200
    assert client.get(url, headers=auth_headers).status_code == 404
    assert client.delete(url, headers=auth_headers).status_code == 404
    assert client.get(f"/{kind}", headers=auth_headers).json()["count"] == 0
    if kind == "quizzes":
        with TestSession() as db:
            assert db.query(QuizQuestion).filter_by(quiz_id=item_id).count() == 0
            assert db.query(QuizAttempt).filter_by(quiz_id=item_id).count() == 0
        assert client.post(f"{url}/submit", headers=auth_headers, json={"answers": [0]}).status_code == 404
    else:
        assert client.get(f"/sessions/{session['id']}", headers=auth_headers).status_code == 200
        assert client.get("/dashboard/me", headers=auth_headers).json()["summary"]["completed_units"] == 1
        # Repeating finish must not recreate a deleted note.
        assert client.post(f"/sessions/{session['id']}/finish", headers=auth_headers).status_code == 200
        assert client.get("/notes", headers=auth_headers).json()["count"] == 0
