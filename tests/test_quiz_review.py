import pytest
from sqlalchemy import create_engine, inspect, text

from app.models.study_content import Quiz, QuizAttempt, QuizQuestion
from app.services.content_service import _option_explanation
from scripts.migrate_schema import migrate_quiz_explanations
from conftest import TestSession


def saved_quiz(client, auth_headers, *, legacy=False):
    user_id = client.get("/auth/me", headers=auth_headers).json()["id"]
    with TestSession() as db:
        quiz = Quiz(user_id=user_id, title="환경 복습", subject="사회")
        db.add(quiz)
        db.flush()
        question = QuizQuestion(
            quiz_id=quiz.id, question="하천의 오염된 물은 어떻게 해야 하나요?",
            options=["처리 없이 배출", "오염물질을 제거한 후 배출", "숲의 면적 측정", "홍수량 측정"],
            correct_index=1, explanation="오염물질을 제거한 뒤 배출해야 하천의 수질과 생물을 보호할 수 있습니다.",
            option_explanations=None if legacy else [
                "처리 없이 배출하면 물속의 오염물질이 하천으로 흘러갑니다.", "자료의 설명과 일치합니다.",
                "숲의 면적은 하천으로 흘러가는 물의 정화 과정이 아닙니다.", "홍수량은 오염물질의 제거 여부를 설명하지 못합니다.",
            ],
        )
        db.add(question)
        db.commit()
        return quiz.id


def test_wrong_answer_has_specific_reason_correct_answer_and_saved_review(client, auth_headers):
    quiz_id = saved_quiz(client, auth_headers)
    detail = client.get(f"/quizzes/{quiz_id}", headers=auth_headers).json()["quiz"]
    assert set(detail["questions"][0]) == {"id", "question", "options"}  # No answer leakage before submission.
    assert client.get(f"/quizzes/{quiz_id}/review", headers=auth_headers).status_code == 404
    response = client.post(f"/quizzes/{quiz_id}/submit", headers=auth_headers, json={"answers": [0]})
    assert response.status_code == 200
    result = response.json()
    assert result["score"] == 0 and result["correct_count"] == 0
    item = result["results"][0]
    assert item["selected_index"] == 0 and item["correct_index"] == 1
    assert "처리 없이" in item["wrong_reason"]
    assert "오염물질을 제거" in item["correct_answer"]
    assert "수질과 생물" in item["explanation"]
    assert item["review_tip"]
    assert client.get(f"/quizzes/{quiz_id}/review", headers=auth_headers).json() == result
    with TestSession() as db:
        assert db.query(QuizAttempt).filter_by(quiz_id=quiz_id).count() == 1
    assert client.get("/quizzes", headers=auth_headers).json()["quizzes"][0]["attempt_count"] == 1


def test_correct_answer_and_latest_review_do_not_overwrite_first_attempt(client, auth_headers):
    quiz_id = saved_quiz(client, auth_headers)
    first = client.post(f"/quizzes/{quiz_id}/submit", headers=auth_headers, json={"answers": [0]}).json()
    second = client.post(f"/quizzes/{quiz_id}/submit", headers=auth_headers, json={"answers": [1]}).json()
    assert second["score"] == 100 and second["results"][0]["wrong_reason"] is None
    assert first["attempt_id"] != second["attempt_id"]
    assert client.get(f"/quizzes/{quiz_id}/review", headers=auth_headers).json()["attempt_id"] == second["attempt_id"]
    with TestSession() as db:
        assert db.get(QuizAttempt, first["attempt_id"]).answers == [0]
        assert db.query(QuizAttempt).filter_by(quiz_id=quiz_id).count() == 2


def test_old_quiz_uses_existing_source_explanation_without_inventing_provenance(client, auth_headers):
    quiz_id = saved_quiz(client, auth_headers, legacy=True)
    item = client.post(f"/quizzes/{quiz_id}/submit", headers=auth_headers, json={"answers": [2]}).json()["results"][0]
    assert "숲의 면적 측정" in item["wrong_reason"] and "오염물질을 제거한 후 배출" in item["wrong_reason"]
    assert "대한 설명으로 구성" not in item["wrong_reason"]
    assert "수질과 생물" in item["explanation"]


@pytest.mark.parametrize("answers", [[-1], [4], [True], ["1"], [1.0], [], [0, 1]])
def test_invalid_choices_are_rejected_before_saving_attempt(client, auth_headers, answers):
    quiz_id = saved_quiz(client, auth_headers)
    assert client.post(f"/quizzes/{quiz_id}/submit", headers=auth_headers, json={"answers": answers}).status_code == 422
    with TestSession() as db:
        assert db.query(QuizAttempt).count() == 0


def test_another_user_cannot_read_or_submit_quiz_review(client, auth_headers):
    quiz_id = saved_quiz(client, auth_headers)
    client.post(f"/quizzes/{quiz_id}/submit", headers=auth_headers, json={"answers": [0]})
    other = client.post("/auth/signup", json={"email": "quiz-other@example.com", "password": "strong-password", "name": "다른 학생"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/quizzes/{quiz_id}/review", headers=headers).status_code == 404
    assert client.post(f"/quizzes/{quiz_id}/submit", headers=headers, json={"answers": [1]}).status_code == 404


def test_invalid_legacy_attempt_does_not_crash_or_display_zero_numbered_choice(client, auth_headers):
    quiz_id = saved_quiz(client, auth_headers, legacy=True)
    with TestSession() as db:
        quiz = db.get(Quiz, quiz_id)
        db.add(QuizAttempt(quiz_id=quiz_id, user_id=quiz.user_id, answers=[-1], score=0, total_questions=1))
        db.commit()
    response = client.get(f"/quizzes/{quiz_id}/review", headers=auth_headers)
    assert response.status_code == 409 and "다시 풀어" in response.json()["detail"]


def test_generated_feedback_stays_aligned_after_shuffling(client, auth_headers):
    created = client.post("/quizzes", headers=auth_headers, json={"subject": "수학", "topic": "도형의 방정식", "question_count": 3})
    assert created.status_code == 201
    with TestSession() as db:
        quiz = db.get(Quiz, created.json()["quiz"]["id"])
        assert quiz.questions
        for question in quiz.questions:
            assert len(question.option_explanations) == len(question.options) == 4
            assert "일치합니다" in question.option_explanations[question.correct_index]
            assert all(isinstance(reason, str) and reason for reason in question.option_explanations)


def test_distractor_feedback_uses_source_question_or_known_changed_condition():
    candidates = [{"question": "숲은 어떤 역할을 하나요?", "answer": "숲은 동물의 서식지입니다."}]
    reason = _option_explanation(candidates[0]["answer"], "물을 정화합니다.", "물을 어떻게 처리하나요?", candidates)
    assert "숲은 어떤 역할" in reason and "물을 어떻게 처리" in reason
    assert "조건이나 관계를 바꾼" in _option_explanation("온도가 감소합니다.", "온도가 증가합니다.", "온도의 변화는?", [])


def test_quiz_schema_upgrade_preserves_legacy_rows_and_is_idempotent():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE quiz_questions (id INTEGER PRIMARY KEY, explanation TEXT)"))
        connection.execute(text("INSERT INTO quiz_questions VALUES (1, '기존 해설')"))
        migrate_quiz_explanations(connection)
        migrate_quiz_explanations(connection)
        assert "option_explanations" in {item["name"] for item in inspect(connection).get_columns("quiz_questions")}
        row = connection.execute(text("SELECT explanation, option_explanations FROM quiz_questions")).one()
        assert row == ("기존 해설", None)
    engine.dispose()
