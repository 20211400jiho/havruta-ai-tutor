from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_tutor import generate_tutor_answer

router = APIRouter()


class RagAskRequest(BaseModel):
    question: str
    school_level: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    top_k: Optional[int] = 3


class RagAskResponse(BaseModel):
    answer: str
    mode: str
    contexts: list
    retrieved_contexts: list


@router.post("/ask", response_model=RagAskResponse)
def ask_rag(request: RagAskRequest):
    try:
        result = generate_tutor_answer(
            question=request.question,
            school_level=request.school_level,
            grade=request.grade,
            subject=request.subject,
            top_k=request.top_k or 3,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG tutor generation failed: {exc}")

    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="Unexpected response format from RAG tutor service")

    return {
        "answer": result.get("answer", ""),
        "mode": result.get("mode", "general_gpt"),
        "contexts": result.get("contexts", []) or [],
        "retrieved_contexts": result.get("retrieved_contexts", []) or [],
    }
