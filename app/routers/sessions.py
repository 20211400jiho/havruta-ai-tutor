from datetime import UTC, datetime

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
from app.services.tutor_service import initial_question, tutor_reply


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
        "created_at": message.created_at,
    }


def session_dict(session: ChatSession, include_messages: bool = False) -> dict:
    result = {
        "id": session.id,
        "room_id": session.room_id,
        "user_id": session.user_id,
        "topic": session.topic,
        "state": session.state,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }
    if include_messages:
        result["messages"] = [message_dict(message) for message in session.messages]
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = ensure_room_access(db, payload.room_id, user.id)
    session = ChatSession(room_id=payload.room_id, user_id=user.id, topic=payload.topic, state="questioning")
    db.add(session)
    db.flush()
    question, contexts = initial_question(db, payload.topic, room.subject or "일반")
    ai_message = Message(session_id=session.id, sender_type="ai", content=question)
    db.add(ai_message)
    db.flush()
    for context in contexts:
        if context.chunk_id:
            db.add(RagReference(message_id=ai_message.id, chunk_id=context.chunk_id, relevance_score=context.score))
    db.commit()
    db.refresh(session)
    return {"session": session_dict(session, include_messages=True)}


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
    return {"session": session_dict(session, include_messages=True)}


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
    user_message = Message(session_id=session.id, sender_type="user", content=payload.content.strip())
    db.add(user_message)
    db.flush()
    subject = session.room.subject if session.room and session.room.subject else "일반"
    reply, feedback_data, contexts = tutor_reply(
        db,
        session.topic or subject,
        payload.content,
        subject,
    )
    feedback = AIFeedback(session_id=session.id, message_id=user_message.id, **feedback_data)
    ai_message = Message(session_id=session.id, sender_type="ai", content=reply)
    db.add_all([feedback, ai_message])
    db.flush()
    for context in contexts:
        if context.chunk_id:
            db.add(RagReference(message_id=ai_message.id, chunk_id=context.chunk_id, relevance_score=context.score))
    session.state = "questioning"
    db.commit()
    db.refresh(ai_message)
    return {"message": message_dict(ai_message), "feedback": feedback_data}


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
