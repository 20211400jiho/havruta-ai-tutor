from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.connection_manager import manager


router = APIRouter(
    prefix="/chat",
    tags=["실시간 채팅"]
)


# WebSocket 채팅
@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int
):
    # 접속
    await manager.connect(room_id, websocket)

    try:
        while True:
            # 메시지 받기
            message = await websocket.receive_text()

            # 같은 방 사람들에게 메시지 전달
            await manager.broadcast(
                room_id,
                message
            )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)