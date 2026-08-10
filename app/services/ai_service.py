from openai import AsyncOpenAI

from app.database.config import settings


async def ask_gpt(user_message: str) -> str:
    if settings.ai_provider != "openai" or not settings.openai_api_key:
        return "OpenAI API 키가 설정되지 않았습니다."
    try:
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )
        response = await client.responses.create(
            model=settings.openai_model,
            reasoning={"effort": settings.openai_reasoning_effort},
            instructions=(
                "너는 중학생과 고등학생의 학습을 돕는 하브루타 AI 튜터야. "
                "학생이 스스로 생각할 수 있도록 친절하게 설명하고, "
                "필요할 때는 짧은 질문을 던져 사고를 유도해."
            ),
            input=user_message,
        )
        return response.output_text
    except Exception as error:
        print(f"OpenAI API 오류: {error}")
        return "AI 답변을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
