from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.chat import Message, SenderType
from app.database.database import get_db
from app.services.ai_service import client


router = APIRouter(
    prefix="/quiz",
    tags=["퀴즈"]
)


@router.post("/session/{session_id}")
async def create_quiz(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 채팅 세션의 학습 내용을 바탕으로
    객관식 퀴즈 3문제를 생성한다.
    """

    # 해당 세션의 대화 내용을 가져온다.
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail="해당 학습 세션의 대화 기록이 없습니다."
        )

    # 학생과 AI의 대화를 하나의 문자열로 만든다.
    conversation_text = ""

    for message in messages:
        if message.sender_type == SenderType.USER.value:
            conversation_text += f"학생: {message.content}\n"

        elif message.sender_type == SenderType.AI.value:
            conversation_text += f"AI 튜터: {message.content}\n"

    try:
        response = await client.responses.create(
            model="gpt-5-mini",
            instructions=(
                "너는 중학생과 고등학생을 위한 학습 퀴즈 생성 AI야. "
                "제공된 학습 대화 내용만 바탕으로 객관식 문제 3개를 만들어. "
                "각 문제는 보기 4개를 제공하고 정답은 하나만 있어야 해. "
                "너무 어렵거나 학습 내용과 관계없는 문제는 만들지 마. "
                "출력은 한국어로 하고, 문제 / 보기 / 정답 / 해설 순서로 작성해."
            ),
            input=(
                "다음 학습 대화를 바탕으로 퀴즈 3문제를 만들어줘.\n\n"
                f"{conversation_text}"
            )
        )

        return {
            "session_id": session_id,
            "quiz": response.output_text
        }

    except Exception as error:
        print(f"퀴즈 생성 오류: {error}")

        raise HTTPException(
            status_code=500,
            detail="퀴즈 생성 중 오류가 발생했습니다."
        )