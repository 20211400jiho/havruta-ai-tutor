from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.config import settings
from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import RagSearchRequest
from app.services.curriculum_catalog import get_subject_catalog
from app.services.rag_service import has_subject_documents, index_local_documents, search


router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/catalog")
def curriculum_catalog(
    subject: str,
    _: User = Depends(get_current_user),
) -> dict:
    catalog = get_subject_catalog(subject)
    if catalog is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{subject.strip()} 과목의 2022 교육과정 RAG 카탈로그가 없습니다.",
        )
    return catalog


@router.post("/index")
def index_documents(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    count = index_local_documents(db)
    return {"message": "로컬 JSON 자료 인덱싱이 완료되었습니다.", "new_chunks": count}


@router.get("/status")
def subject_status(
    subject: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    normalized_subject = subject.strip()
    return {
        "subject": normalized_subject,
        "curriculum_year": settings.rag_curriculum_year,
        "alignment_policy": "source_or_achievement_standard",
        "available": has_subject_documents(
            db,
            normalized_subject,
            settings.rag_curriculum_year,
        ),
    }


@router.post("/search")
def search_documents(
    payload: RagSearchRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    results = search(db, payload.query, payload.top_k, payload.subject)
    return {
        "query": payload.query,
        "curriculum_year": settings.rag_curriculum_year,
        "alignment_policy": "source_or_achievement_standard",
        "results": [
            {
                "source_id": result.source_id,
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata,
            }
            for result in results
        ],
    }
