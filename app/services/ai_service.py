"""
OpenAI GPT와 통신하는 서비스
"""

from dotenv import load_dotenv
from openai import AsyncOpenAI

# .env 파일에 저장된 환경변수를 불러온다.
load_dotenv()

# 비동기 방식의 OpenAI 클라이언트를 생성한다.
client = AsyncOpenAI()


async def ask_gpt(user_message: str) -> str:
    """
    사용자의 메시지를 GPT에게 보내고
    생성된 답변을 문자열로 반환한다.
    """

    try:
        response = await client.responses.create(
            model="gpt-5-mini",
            instructions=(
                "너는 중학생과 고등학생의 학습을 돕는 하브루타 AI 튜터야. "
                "학생이 스스로 생각할 수 있도록 친절하게 설명하고, "
                "필요할 때는 짧은 질문을 던져 사고를 유도해."
            ),
            input=user_message
        )

        return response.output_text

    except Exception as error:
        print(f"OpenAI API 오류: {error}")
        return "AI 답변을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."