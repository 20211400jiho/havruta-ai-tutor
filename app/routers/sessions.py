from datetime import UTC, datetime
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.ai_feedback import AIFeedback
from app.models.chat import ChatSession, Message
from app.models.document import RagReference
from app.models.learning import LearningRecord, LearningRoom, RoomMember
from app.models.user import User
from app.schemas.chat import MessageCreateRequest, SessionCreateRequest
from app.services.content_service import create_note_for_session
from app.database.config import settings
from app.rag.curriculum import is_valid_curriculum_selection
from app.services.rate_limit_service import AIUsageLimitError, check_and_record_ai_usage
from app.rag.tutor import conversation_stage, initial_question, source_summary, tutor_reply


router = APIRouter(prefix="/sessions", tags=["AI 학습 세션"])


def ensure_room_access(db: Session, room_id: int, user_id: int) -> LearningRoom:
    room = db.get(LearningRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="학습방을 찾을 수 없습니다.")
    member = db.query(RoomMember).filter_by(room_id=room_id, user_id=user_id).first()
    if room.owner_id != user_id and member is None:
        raise HTTPException(status_code=403, detail="학습방 접근 권한이 없습니다.")
    return room


def message_dict(message: Message) -> dict:
    return {
        "id": message.id,
        "sender_type": message.sender_type,
        "content": message.content,
        "response_meta": message.response_meta_json,
        "created_at": message.created_at,
    }


def resolve_learning_scope(
    room: LearningRoom,
    school_level: str | None,
    grade: str | None,
) -> tuple[str | None, str | None]:
    room_grade = room.grade or ""
    resolved_level = school_level
    if not resolved_level:
        resolved_level = "고등학교" if "고등" in room_grade else "중학교" if "중" in room_grade else None
    resolved_grade = grade
    if not resolved_grade:
        grade_match = re.search(r"([1-3])\s*학년", room_grade)
        resolved_grade = f"{grade_match.group(1)}학년" if grade_match else None
    return resolved_level, resolved_grade


def enforce_ai_quota(db: Session, user_id: int, action: str) -> None:
    try:
        check_and_record_ai_usage(db, user_id, action)
    except AIUsageLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc


def session_dict(session: ChatSession, include_messages: bool = False) -> dict:
    result = {
        "id": session.id,
        "room_id": session.room_id,
        "user_id": session.user_id,
        "topic": session.topic,
        "unit_code": session.unit_code,
        "school_level": session.school_level,
        "grade": session.grade,
        "state": session.state,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }
    if include_messages:
        result["messages"] = [
            message_dict(message)
            for message in sorted(session.messages, key=lambda item: (item.created_at, item.id))
        ]
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = ensure_room_access(db, payload.room_id, user.id)
    school_level, grade = resolve_learning_scope(room, payload.school_level, payload.grade)
    if payload.unit_code and not is_valid_curriculum_selection(
        room.subject or "일반",
        school_level,
        grade,
        payload.unit_code,
    ):
        raise HTTPException(status_code=422, detail="과목·학교급·학년·단원 조합이 올바르지 않습니다.")
    session = ChatSession(
        room_id=payload.room_id,
        user_id=user.id,
        topic=payload.topic,
        unit_code=payload.unit_code,
        school_level=school_level,
        grade=grade,
        state="questioning",
    )
    db.add(session)
    db.flush()
    question, contexts = initial_question(
        db,
        payload.topic,
        room.subject or "일반",
        unit_code=payload.unit_code,
        school_level=school_level,
        grade=grade,
    )
    response_meta = {
        "ai_provider": "question_template",
        "retriever": contexts[0].metadata.get("retriever", "lexical") if contexts else "none",
        "grounded": bool(contexts),
        "curriculum_year": settings.rag_curriculum_year,
        "stage": "개념 설명",
        "sources": [source_summary(item) for item in contexts],
    }
    ai_message = Message(
        session_id=session.id,
        sender_type="ai",
        content=question,
        response_meta_json=response_meta,
    )
    db.add(ai_message)
    db.flush()
    for context in contexts:
        if context.chunk_id:
            db.add(RagReference(message_id=ai_message.id, chunk_id=context.chunk_id, relevance_score=context.score))
    db.commit()
    db.refresh(session)
    return {
        "session": session_dict(session, include_messages=True),
        "response_meta": response_meta,
    }


@router.get("")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.started_at.desc())
        .all()
    )
    return {"count": len(sessions), "sessions": [session_dict(item) for item in sessions]}


@router.get("/{session_id}")
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="학습 세션을 찾을 수 없습니다.")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")
    serialized = session_dict(session, include_messages=True)
    return {
        "session": serialized,
        "response_meta": {
            "stage": conversation_stage(serialized["messages"]),
            "curriculum_year": settings.rag_curriculum_year,
        },
    }


@router.post("/{session_id}/messages")
def send_message(
    session_id: int,
    payload: MessageCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="학습 세션을 찾을 수 없습니다.")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")
    if session.state == "finished":
        raise HTTPException(status_code=409, detail="이미 종료된 세션입니다.")
    enforce_ai_quota(db, user.id, "tutor_message")
    user_message = Message(session_id=session.id, sender_type="user", content=payload.content.strip())
    db.add(user_message)
    db.flush()
    history = (
        db.query(Message)
        .filter(Message.session_id == session.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    subject = session.room.subject if session.room and session.room.subject else "일반"
    reply, feedback_data, contexts, response_meta = tutor_reply(
        db,
        session.topic or subject,
        payload.content,
        subject,
        unit_code=session.unit_code,
        conversation_history=[message_dict(message) for message in history],
        school_level=session.school_level,
        grade=session.grade,
    )
    feedback = AIFeedback(
        session_id=session.id,
        message_id=user_message.id,
        score=feedback_data["score"],
        summary=feedback_data["summary"],
        strengths=feedback_data["strengths"],
        improvements=feedback_data["improvements"],
        followup_question=feedback_data["followup_question"],
    )
    ai_message = Message(
        session_id=session.id,
        sender_type="ai",
        content=reply,
        response_meta_json=response_meta,
    )
    db.add_all([feedback, ai_message])
    db.flush()
    for context in contexts:
        if context.chunk_id:
            db.add(RagReference(message_id=ai_message.id, chunk_id=context.chunk_id, relevance_score=context.score))
    session.state = "questioning"
    db.commit()
    db.refresh(ai_message)
    return {
        "message": message_dict(ai_message),
        "feedback": feedback_data,
        "response_meta": response_meta,
    }


@router.post("/{session_id}/finish")
def finish_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="학습 세션을 찾을 수 없습니다.")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")
    if session.learning_record:
        return {"message": "이미 종료된 세션입니다.", "record_id": session.learning_record.id}
    total_messages = db.query(func.count(Message.id)).filter(Message.session_id == session.id).scalar() or 0
    average = db.query(func.avg(AIFeedback.score)).filter(AIFeedback.session_id == session.id).scalar()
    session.state = "finished"
    session.ended_at = datetime.now(UTC).replace(tzinfo=None)
    record = LearningRecord(
        user_id=user.id,
        room_id=session.room_id,
        session_id=session.id,
        total_messages=total_messages,
        ai_score_avg=round(float(average)) if average is not None else None,
        completed_at=session.ended_at,
    )
    db.add(record)
    note = create_note_for_session(db, session)
    db.commit()
    db.refresh(record)
    return {"message": "학습 세션이 완료되었습니다.", "record_id": record.id, "note_id": note.id}
