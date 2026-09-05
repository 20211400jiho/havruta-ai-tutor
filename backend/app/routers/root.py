from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database.config import settings
from app.database.connection import get_db
from app.models.document import DocumentChunk
from app.services.connection_manager import manager
from app.services.rag_service import _chroma_collection

# 기본 API를 관리하는 Router
router = APIRouter(
    tags=["서버 확인"]
)


# 서버가 정상적으로 실행 중인지 확인하는 API
@router.get(
    "/",
    summary="서버 상태 확인",
    description="하브루타 AI 튜터 백엔드 서버의 실행 상태를 확인합니다."
)
def root():
    return {
        "status": "ok",
        "service": "havruta-ai-tutor",
        "docs": "/docs",
    }


@router.get("/health/live", summary="프로세스 상태 확인")
def live():
    return {"status": "ok", "service": "havruta-ai-tutor"}


@router.get("/health/ready", summary="발표·배포 준비 상태 확인")
def ready(db: Session = Depends(get_db)) -> dict:
    database_ok = False
    lexical_documents = 0
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
        lexical_documents = db.query(func.count(DocumentChunk.id)).scalar() or 0
    except Exception:
        db.rollback()

    chroma_available = False
    chroma_count = 0
    chroma_error = None
    if settings.rag_provider.strip().lower() in {"auto", "chroma"}:
        try:
            collection = _chroma_collection()
            chroma_count = collection.count()
            chroma_available = chroma_count > 0
        except Exception as exc:
            chroma_error = type(exc).__name__

    configured_ai = "openai"
    ai_ready = bool(settings.openai_api_key)
    rag_ready = chroma_available or lexical_documents > 0
    return {
        "status": "ready" if database_ok and rag_ready else "degraded",
        "database": {"ready": database_ok},
        "rag": {
            "ready": rag_ready,
            "provider": "chroma" if chroma_available else "lexical" if lexical_documents else "none",
            "chroma_documents": chroma_count,
            "lexical_documents": lexical_documents,
            "curriculum_year": settings.rag_curriculum_year,
            "diagnostic": chroma_error,
        },
        "ai": {
            "configured_provider": configured_ai,
            "provider_configured": ai_ready,
            "rule_fallback_ready": True,
        },
        "realtime": {
            "redis_configured": bool(settings.redis_url),
            "redis_connected": manager.redis is not None,
            "local_websocket_fallback_ready": True,
        },
    }
