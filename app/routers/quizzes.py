from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.study_content import Quiz, QuizAttempt
from app.models.user import User
from app.schemas.study_content import QuizGenerateRequest, QuizSubmitRequest
from app.services.content_service import QuizSourceNotFoundError, generate_quiz
from app.rag.curriculum import is_valid_curriculum_selection


router = APIRouter(prefix="/quizzes", tags=["복습 퀴즈"])


def quiz_summary(quiz: Quiz) -> dict:
    best_score = max((attempt.score for attempt in quiz.attempts), default=None)
    return {
        "id": quiz.id,
        "title": quiz.title,
        "subject": quiz.subject,
        "total_questions": len(quiz.questions),
        "best_score": best_score,
        "created_at": quiz.created_at,
    }


@router.get("")
def list_quizzes(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    quizzes = db.query(Quiz).filter(Quiz.user_id == user.id).order_by(Quiz.created_at.desc()).all()
    return {"count": len(quizzes), "quizzes": [quiz_summary(quiz) for quiz in quizzes]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_quiz(
    payload: QuizGenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.unit_code and not is_valid_curriculum_selection(
        payload.subject or "",
        payload.school_level,
        payload.grade,
        payload.unit_code,
    ):
        raise HTTPException(status_code=422, detail="과목·학교급·학년·단원 조합이 올바르지 않습니다.")
    try:
        quiz = generate_quiz(
            db,
            user.id,
            payload.topic,
            payload.question_count,
            payload.subject,
            payload.unit_code,
            payload.school_level,
            payload.grade,
        )
    except QuizSourceNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"quiz": quiz_summary(quiz)}


@router.get("/{quiz_id}")
def get_quiz(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")
    if quiz.user_id != user.id:
        raise HTTPException(status_code=403, detail="퀴즈 접근 권한이 없습니다.")
    result = quiz_summary(quiz)
    result["questions"] = [
        {"id": question.id, "question": question.question, "options": question.options}
        for question in quiz.questions
    ]
    return {"quiz": result}


@router.post("/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None or quiz.user_id != user.id:
        raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")
    if len(payload.answers) != len(quiz.questions):
        raise HTTPException(status_code=422, detail="모든 문제의 답을 제출해주세요.")
    correct_count = sum(answer == question.correct_index for answer, question in zip(payload.answers, quiz.questions))
    score = round(correct_count / len(quiz.questions) * 100) if quiz.questions else 0
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        answers=payload.answers,
        score=score,
        total_questions=len(quiz.questions),
    )
    db.add(attempt)
    db.commit()
    return {
        "score": score,
        "correct_count": correct_count,
        "total_questions": len(quiz.questions),
        "results": [
            {
                "correct_index": question.correct_index,
                "explanation": question.explanation,
                "is_correct": payload.answers[index] == question.correct_index,
            }
            for index, question in enumerate(quiz.questions)
        ],
    }
