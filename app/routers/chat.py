import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.chat import RoomChatMessage
from app.models.learning import LearningRoom, RoomMember
from app.models.user import User
from app.schemas.chat import CollaborativeFeedbackRequest
from app.services.collaborative_service import analyze_room_discussion
from app.services.connection_manager import manager
from app.rag.curriculum import is_valid_curriculum_selection
from app.services.rate_limit_service import AIUsageLimitError, check_and_record_ai_usage
from app.utils.security import verify_access_token


router = APIRouter(prefix="/chat", tags=["실시간 채팅"])


def has_room_access(db: Session, room_id: int, user_id: int) -> bool:
    room = db.get(LearningRoom, room_id)
    if room is None or room.status != "active":
        return False
    if room.owner_id == user_id:
        return True
    return db.query(RoomMember).filter_by(room_id=room_id, user_id=user_id).first() is not None


def chat_message_dict(message: RoomChatMessage) -> dict:
    return {
        "id": message.id,
        "room_id": message.room_id,
        "user_id": message.user_id,
        "user_name": message.user.name,
        "content": message.content,
        "created_at": message.created_at,
    }


@router.get("/rooms/{room_id}/messages")
def room_message_history(
    room_id: int,
    limit: int = Query(default=100, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not has_room_access(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="학습방 채팅 접근 권한이 없습니다.")
    messages = (
        db.query(RoomChatMessage)
        .options(joinedload(RoomChatMessage.user))
        .filter(RoomChatMessage.room_id == room_id)
        .order_by(RoomChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()
    return {"count": len(messages), "messages": [chat_message_dict(message) for message in messages]}


@router.post("/rooms/{room_id}/ai-feedback")
def collaborative_feedback(
    room_id: int,
    payload: CollaborativeFeedbackRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not has_room_access(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="학습방 토론 분석 권한이 없습니다.")
    room = db.get(LearningRoom, room_id)
    if payload.unit_code and not is_valid_curriculum_selection(
        room.subject or "",
        payload.school_level,
        payload.grade,
        payload.unit_code,
    ):
        raise HTTPException(status_code=422, detail="과목·학교급·학년·단원 조합이 올바르지 않습니다.")
    try:
        check_and_record_ai_usage(db, user.id, "collaborative_feedback")
    except AIUsageLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    try:
        return analyze_room_discussion(
            db,
            room,
            payload.topic,
            payload.unit_code,
            payload.school_level,
            payload.grade,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    db: Session = Depends(get_db),
) -> None:
    await websocket.accept()
    try:
        auth_message = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        auth_payload = json.loads(auth_message)
        token = str(auth_payload.get("token", "")) if auth_payload.get("type") == "authenticate" else ""
    except WebSocketDisconnect:
        return
    except (TimeoutError, json.JSONDecodeError):
        await websocket.close(code=4401, reason="인증 메시지가 필요합니다.")
        return

    user_id = verify_access_token(token)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        await websocket.close(code=4401, reason="인증이 필요합니다.")
        return
    if not has_room_access(db, room_id, user.id):
        await websocket.close(code=4403, reason="학습방 접근 권한이 없습니다.")
        return

    manager.connect(room_id, websocket)
    await websocket.send_json({"type": "authenticated", "user_id": user.id, "room_id": room_id})
    await manager.broadcast(
        room_id,
        {"type": "presence", "action": "joined", "user_id": user.id, "user_name": user.name},
    )
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                incoming = json.loads(raw_message)
                content = str(incoming.get("content", "")).strip()
            except json.JSONDecodeError:
                content = raw_message.strip()
            if not content:
                await websocket.send_json({"type": "error", "detail": "메시지를 입력해주세요."})
                continue
            if len(content) > 5000:
                await websocket.send_json({"type": "error", "detail": "메시지는 5000자까지 입력할 수 있습니다."})
                continue

            message = RoomChatMessage(room_id=room_id, user_id=user.id, content=content)
            db.add(message)
            db.commit()
            db.refresh(message)
            message.user = user
            await manager.broadcast(room_id, {"type": "message", "message": chat_message_dict(message)})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(
            room_id,
            {"type": "presence", "action": "left", "user_id": user.id, "user_name": user.name},
        )
