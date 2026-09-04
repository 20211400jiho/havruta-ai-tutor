from calendar import monthrange
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.learning import LearningRecord
from app.models.study_content import QuizAttempt, StudyNote
from app.models.user import User


router = APIRouter(prefix="/dashboard", tags=["학습 통계"])


@router.get("/me")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    records = (
        db.query(LearningRecord)
        .options(joinedload(LearningRecord.session))
        .filter(LearningRecord.user_id == user.id)
        .order_by(LearningRecord.created_at.desc())
        .all()
    )
    average = db.query(func.avg(LearningRecord.ai_score_avg)).filter(LearningRecord.user_id == user.id).scalar()
    average_value = round(float(average), 1) if average is not None else None
    completed_units = len({record.session.unit_code for record in records if record.session.unit_code})
    completed_quizzes = db.query(func.count(QuizAttempt.id)).filter(QuizAttempt.user_id == user.id).scalar() or 0
    review_topics = list(dict.fromkeys(
        record.session.topic
        for record in records
        if record.session.topic and (record.ai_score_avg is None or record.ai_score_avg < 60)
    ))[:5]
    strong_topics = list(dict.fromkeys(
        record.session.topic
        for record in records
        if record.session.topic and record.ai_score_avg is not None and record.ai_score_avg >= 80
    ))[:5]
    explanation_level = (
        "우수" if average_value is not None and average_value >= 80
        else "충분함" if average_value is not None and average_value >= 60
        else "보완 필요" if average_value is not None
        else "학습 전"
    )
    return {
        "user": {"id": user.id, "name": user.name, "grade": user.grade},
        "summary": {
            "completed_sessions": len(records),
            "completed_units": completed_units,
            "completed_quizzes": completed_quizzes,
            "total_messages": sum(record.total_messages for record in records),
            "average_score": average_value,
            "explanation_level": explanation_level,
        },
        "review_topics": review_topics,
        "strong_topics": strong_topics,
        "recent_records": [
            {
                "id": record.id,
                "room_id": record.room_id,
                "session_id": record.session_id,
                "total_messages": record.total_messages,
                "average_score": record.ai_score_avg,
                "completed_at": record.completed_at,
                "topic": record.session.topic,
            }
            for record in records[:20]
        ],
    }


@router.get("/calendar")
def calendar_records(
    year: int = Query(ge=2020, le=2100),
    month: int = Query(ge=1, le=12),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    start = datetime(year, month, 1)
    end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1)
    records = (
        db.query(LearningRecord)
        .options(joinedload(LearningRecord.session))
        .filter(
            LearningRecord.user_id == user.id,
            LearningRecord.completed_at >= start,
            LearningRecord.completed_at < end,
        )
        .order_by(LearningRecord.completed_at.asc())
        .all()
    )
    notes = (
        db.query(StudyNote)
        .filter(
            StudyNote.user_id == user.id,
            StudyNote.created_at >= start,
            StudyNote.created_at < end,
        )
        .order_by(StudyNote.created_at.asc())
        .all()
    )
    events: dict[str, dict] = {}
    for record in records:
        if not record.completed_at:
            continue
        key = record.completed_at.date().isoformat()
        event = events.setdefault(key, {"date": key, "records": [], "notes": []})
        event["records"].append({
            "id": record.id,
            "session_id": record.session_id,
            "topic": record.session.topic,
            "unit_code": record.session.unit_code,
            "explanation_level": "우수" if record.ai_score_avg is not None and record.ai_score_avg >= 80 else "충분함" if record.ai_score_avg is not None and record.ai_score_avg >= 60 else "보완 필요",
            "average_score": record.ai_score_avg,
        })
    for note in notes:
        key = note.created_at.date().isoformat()
        event = events.setdefault(key, {"date": key, "records": [], "notes": []})
        event["notes"].append({"id": note.id, "title": note.title, "subject": note.subject})
    return {
        "year": year,
        "month": month,
        "days_in_month": monthrange(year, month)[1],
        "events": list(events.values()),
    }
