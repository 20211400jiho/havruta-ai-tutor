from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "하브루타 AI 튜터 백엔드 서버입니다!"}