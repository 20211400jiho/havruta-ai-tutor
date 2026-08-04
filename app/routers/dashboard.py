from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.learning import LearningRecord
from app.models.user import User


router = APIRouter(prefix="/dashboard", tags=["학습 통계"])


@router.get("/me")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    records = (
        db.query(LearningRecord)
        .filter(LearningRecord.user_id == user.id)
        .order_by(LearningRecord.created_at.desc())
        .all()
    )
    average = db.query(func.avg(LearningRecord.ai_score_avg)).filter(LearningRecord.user_id == user.id).scalar()
    return {
        "user": {"id": user.id, "name": user.name, "grade": user.grade},
        "summary": {
            "completed_sessions": len(records),
            "total_messages": sum(record.total_messages for record in records),
            "average_score": round(float(average), 1) if average is not None else None,
        },
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
            for record in records[:10]
        ],
    }
