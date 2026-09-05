from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.config import settings
from app.database.connection import SessionLocal, create_tables
from app.routers.auth import router as auth_router
from app.routers.chat import router as websocket_router
from app.routers.dashboard import router as dashboard_router
from app.routers.rag import router as rag_router
from app.routers.notes import router as notes_router
from app.routers.quizzes import router as quizzes_router
from app.routers.room import router as room_router
from app.routers.root import router as root_router
from app.routers.sessions import router as sessions_router
from app.rag.retriever import index_local_documents
from app.services.connection_manager import manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    db = SessionLocal()
    try:
        index_local_documents(db)
    finally:
        db.close()
    await manager.start()
    try:
        yield
    finally:
        await manager.stop()


app = FastAPI(
    title=settings.app_name,
    description="중·고등학생을 위한 AI 하브루타 학습 시스템 API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router)
app.include_router(auth_router)
app.include_router(room_router)
app.include_router(sessions_router)
app.include_router(rag_router)
app.include_router(dashboard_router)
app.include_router(notes_router)
app.include_router(quizzes_router)
app.include_router(websocket_router)
