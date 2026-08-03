# .env 파일의 환경변수를 불러오기 위한 라이브러리
from dotenv import load_dotenv

# OpenAI API를 사용하기 위한 라이브러리
from openai import OpenAI

# .env 파일 불러오기
load_dotenv()

# OpenAI 클라이언트 생성
client = OpenAI()

try:
    # GPT에게 테스트 메시지 보내기
    response = client.responses.create(
        model="gpt-5-mini",
        input="안녕하세요! 한 문장으로 자기소개해 주세요."
    )

    print("GPT 응답:")
    print(response.output_text)

except Exception as e:
    print("오류 발생!")
    print(e)