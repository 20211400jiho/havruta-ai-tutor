from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import RagSearchRequest
from app.services.rag_service import index_local_documents, search


router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/index")
def index_documents(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    count = index_local_documents(db)
    return {"message": "로컬 수학 자료 인덱싱이 완료되었습니다.", "new_chunks": count}


@router.post("/search")
def search_documents(
    payload: RagSearchRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    results = search(db, payload.query, payload.top_k)
    return {
        "query": payload.query,
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
