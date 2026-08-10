from openai import OpenAI

from app.database.config import settings


def main() -> None:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY를 .env에 설정하세요.")
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        reasoning={"effort": settings.openai_reasoning_effort},
        input="안녕하세요! 한 문장으로 자기소개해 주세요.",
    )
    print("GPT 응답:")
    print(response.output_text)


if __name__ == "__main__":
    main()
