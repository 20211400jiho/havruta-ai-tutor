from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.connection_manager import manager
from app.services.ai_service import ask_gpt


router = APIRouter(
    prefix="/chat",
    tags=["실시간 채팅"]
)


@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int
):
    """
    사용자가 보낸 메시지를 같은 방에 전달하고,
    GPT가 생성한 답변도 같은 방에 전달한다.
    """

    # 사용자를 학습방 WebSocket에 연결한다.
    await manager.connect(room_id, websocket)

    try:
        while True:
            # 사용자 메시지를 받는다.
            user_message = await websocket.receive_text()

            # 사용자 메시지를 같은 방 사람들에게 전달한다.
            await manager.broadcast(
                room_id,
                f"사용자: {user_message}"
            )

            # GPT에게 사용자 메시지를 보내고 답변을 받는다.
            ai_response = await ask_gpt(user_message)

            # GPT 답변을 같은 방 사람들에게 전달한다.
            await manager.broadcast(
                room_id,
                f"AI 튜터: {ai_response}"
            )

    except WebSocketDisconnect:
        # 연결이 종료되면 접속 목록에서 제거한다.
        manager.disconnect(room_id, websocket)

    except Exception as error:
        print(f"WebSocket 오류: {error}")
        manager.disconnect(room_id, websocket)