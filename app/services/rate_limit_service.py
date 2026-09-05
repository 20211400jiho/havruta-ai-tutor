from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.config import settings
from app.models.ai_usage import AIUsageEvent


class AIUsageLimitError(RuntimeError):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


def check_and_record_ai_usage(db: Session, user_id: int, action: str) -> None:
    """Apply per-user OpenAI cost protection and persist the accepted request."""
    now = datetime.now(UTC).replace(tzinfo=None)
    minute_start = now - timedelta(minutes=1)
    day_start = now - timedelta(days=1)
    minute_count = (
        db.query(func.count(AIUsageEvent.id))
        .filter(AIUsageEvent.user_id == user_id, AIUsageEvent.created_at >= minute_start)
        .scalar()
        or 0
    )
    if minute_count >= settings.ai_requests_per_minute:
        raise AIUsageLimitError(
            "AI 요청이 잠시 많습니다. 1분 뒤 다시 시도해주세요.",
            retry_after=60,
        )
    day_count = (
        db.query(func.count(AIUsageEvent.id))
        .filter(AIUsageEvent.user_id == user_id, AIUsageEvent.created_at >= day_start)
        .scalar()
        or 0
    )
    if day_count >= settings.ai_requests_per_day:
        raise AIUsageLimitError(
            "오늘 사용할 수 있는 AI 학습 요청을 모두 사용했습니다. 내일 다시 이용해주세요.",
            retry_after=3600,
        )
    db.add(AIUsageEvent(user_id=user_id, action=action))
    db.commit()
