import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.chat import RoomChatMessage
from app.models.learning import LearningRoom, RoomMember
from app.models.user import User
from app.services.connection_manager import manager
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
    except (TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
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
