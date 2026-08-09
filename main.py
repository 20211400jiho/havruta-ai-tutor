from fastapi import FastAPI

# 데이터베이스와 모델 가져오기
from app.database.database import Base, engine
from app.models.user import User
from app.models.room import Room

# 기능별 Router 가져오기
from app.routers.root import router as root_router
from app.routers.auth import router as auth_router
from app.routers.room import router as room_router
from app.routers.chat import router as chat_router
from app.routers.quiz import router as quiz_router
from app.routers.summary import router as summary_router


# 데이터베이스에 정의된 테이블 생성
Base.metadata.create_all(bind=engine)


# FastAPI 서버 설정
app = FastAPI(
    title="하브루타 AI 튜터 API",
    description="중·고등학생을 위한 AI 하브루타 학습 시스템 백엔드 API",
    version="1.0.0"
)


# Router 등록
app.include_router(root_router)
app.include_router(auth_router)
app.include_router(room_router)
app.include_router(chat_router)
app.include_router(quiz_router)
app.include_router(summary_router)