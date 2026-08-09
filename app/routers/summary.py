from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.chat import Message, SenderType
from app.database.database import get_db
from app.services.ai_service import client


router = APIRouter(
    prefix="/summary",
    tags=["요약 노트"]
)


@router.post("/session/{session_id}")
async def create_summary(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 채팅 세션의 학습 내용을 바탕으로
    복습용 요약 노트를 생성한다.
    """

    # 해당 학습 세션의 모든 대화 내용을 가져온다.
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )

    # 해당 세션에 저장된 대화가 없는 경우
    if not messages:
        raise HTTPException(
            status_code=404,
            detail="해당 학습 세션의 대화 기록이 없습니다."
        )

    # DB에 저장된 대화를 하나의 문자열로 만든다.
    conversation_text = ""

    for message in messages:

        if message.sender_type == SenderType.USER.value:
            conversation_text += (
                f"학생: {message.content}\n"
            )

        elif message.sender_type == SenderType.AI.value:
            conversation_text += (
                f"AI 튜터: {message.content}\n"
            )

    try:
        # 학습 대화를 GPT에게 전달하여 요약 노트를 생성한다.
        response = await client.responses.create(
            model="gpt-5-mini",
            instructions=(
                "너는 중학생과 고등학생을 위한 학습 요약 AI야. "
                "제공된 학생과 AI 튜터의 학습 대화를 분석해서 "
                "학생이 나중에 복습하기 좋은 요약 노트를 만들어. "
                "대화에서 실제로 학습한 내용만 사용해야 해. "
                "중요 개념과 핵심 내용을 간단하고 이해하기 쉽게 정리해. "
                "필요한 경우 공식이나 예시도 포함해. "
                "출력은 한국어로 작성해."
            ),
            input=(
                "다음 학습 대화를 복습용 요약 노트로 만들어줘.\n\n"
                f"{conversation_text}"
            )
        )

        return {
            "session_id": session_id,
            "summary": response.output_text
        }

    except Exception as error:
        print(f"요약 노트 생성 오류: {error}")

        raise HTTPException(
            status_code=500,
            detail="요약 노트 생성 중 오류가 발생했습니다."
        )