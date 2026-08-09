"""
OpenAI GPT와 통신하는 서비스
"""

from dotenv import load_dotenv
from openai import AsyncOpenAI


# .env 파일에 저장된 환경변수를 불러온다.
load_dotenv()

# 비동기 방식의 OpenAI 클라이언트를 생성한다.
client = AsyncOpenAI()


async def ask_gpt(
    user_message: str,
    conversation_history: list[dict] | None = None
) -> str:
    """
    이전 대화 내용과 현재 사용자의 메시지를 GPT에게 보내고
    생성된 답변을 문자열로 반환한다.
    """

    try:
        # 이전 대화가 없으면 빈 목록으로 시작한다.
        input_messages = conversation_history or []

        # 현재 사용자의 메시지를 대화 내용에 추가한다.
        input_messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        # GPT에게 이전 대화와 현재 질문을 함께 전달한다.
        response = await client.responses.create(
            model="gpt-5-mini",
            instructions=(
                "너는 중학생과 고등학생의 학습을 돕는 하브루타 AI 튜터야. "
                "이전 대화 내용을 기억하고 이어서 답변해야 해. "
                "학생이 '그거', '아까 거', '그 공식'처럼 이전 내용을 가리키면 "
                "앞선 대화를 참고해서 자연스럽게 이해해야 해. "
                "학생이 스스로 생각할 수 있도록 친절하게 설명하고, "
                "필요할 때는 짧은 질문을 던져 사고를 유도해."
            ),
            input=input_messages
        )

        return response.output_text

    except Exception as error:
        print(f"OpenAI API 오류: {error}")

        return (
            "AI 답변을 생성하는 중 오류가 발생했습니다. "
            "잠시 후 다시 시도해 주세요."
        )