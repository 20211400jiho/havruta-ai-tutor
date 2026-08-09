from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database.chat import ChatSession, Message, SenderType
from app.database.database import get_db
from app.database.learning import LearningRecord
from app.services.ai_service import ask_gpt
from app.services.connection_manager import manager


router = APIRouter(
    prefix="/chat",
    tags=["실시간 채팅"]
)


@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    사용자가 보낸 메시지와 AI 답변을 같은 학습방에 전달하고,
    대화 내용과 학습 기록을 데이터베이스에 저장한다.

    같은 채팅 세션의 이전 메시지를 GPT에게 함께 전달하여
    AI가 앞선 대화 내용을 기억하고 이어서 답변할 수 있게 한다.
    """

    # 새로운 채팅 세션을 생성한다.
    chat_session = ChatSession(
        room_id=room_id,
        user_id=user_id
    )

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    # 채팅 세션과 연결된 학습 기록을 생성한다.
    learning_record = LearningRecord(
        user_id=user_id,
        room_id=room_id,
        session_id=chat_session.id,
        total_messages=0
    )

    db.add(learning_record)
    db.commit()
    db.refresh(learning_record)

    # 사용자를 WebSocket 학습방에 연결한다.
    await manager.connect(room_id, websocket)

    try:
        while True:
            # 사용자가 보낸 새로운 메시지를 받는다.
            user_message = await websocket.receive_text()

            # -------------------------------------------------
            # 1. 현재 메시지를 저장하기 전에 이전 대화를 조회한다.
            # -------------------------------------------------

            previous_messages = (
                db.query(Message)
                .filter(Message.session_id == chat_session.id)
                .order_by(Message.id.asc())
                .all()
            )

            # GPT에게 전달할 이전 대화 목록
            conversation_history = []

            for message in previous_messages:

                # 사용자가 보낸 메시지
                if message.sender_type == SenderType.USER.value:
                    conversation_history.append(
                        {
                            "role": "user",
                            "content": message.content
                        }
                    )

                # AI가 보낸 메시지
                elif message.sender_type == SenderType.AI.value:
                    conversation_history.append(
                        {
                            "role": "assistant",
                            "content": message.content
                        }
                    )

            # -------------------------------------------------
            # 2. 현재 사용자 메시지를 DB에 저장한다.
            # -------------------------------------------------

            user_db_message = Message(
                session_id=chat_session.id,
                sender_type=SenderType.USER.value,
                content=user_message
            )

            db.add(user_db_message)

            # 사용자 메시지 수를 학습 기록에 반영한다.
            learning_record.total_messages += 1

            db.commit()

            # 사용자 메시지를 같은 방 사용자들에게 전달한다.
            await manager.broadcast(
                room_id,
                f"사용자: {user_message}"
            )

            # -------------------------------------------------
            # 3. 이전 대화 + 현재 질문을 GPT에게 전달한다.
            # -------------------------------------------------

            ai_response = await ask_gpt(
                user_message,
                conversation_history
            )

            # -------------------------------------------------
            # 4. AI 답변을 DB에 저장한다.
            # -------------------------------------------------

            ai_db_message = Message(
                session_id=chat_session.id,
                sender_type=SenderType.AI.value,
                content=ai_response
            )

            db.add(ai_db_message)

            # AI 답변도 총 메시지 수에 포함한다.
            learning_record.total_messages += 1

            db.commit()

            # AI 답변을 같은 방 사용자들에게 전달한다.
            await manager.broadcast(
                room_id,
                f"AI 튜터: {ai_response}"
            )

    except WebSocketDisconnect:
        # 정상적으로 연결이 종료되면 종료 시간을 저장한다.
        chat_session.ended_at = datetime.now()
        learning_record.completed_at = datetime.now()

        db.commit()

        manager.disconnect(room_id, websocket)

    except Exception as error:
        print(f"WebSocket 오류: {error}")

        # 오류로 종료된 경우에도 종료 시간을 저장한다.
        chat_session.ended_at = datetime.now()
        learning_record.completed_at = datetime.now()

        db.commit()

        manager.disconnect(room_id, websocket)