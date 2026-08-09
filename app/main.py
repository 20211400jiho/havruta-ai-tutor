from fastapi import FastAPI

from app.routers.rag import router as rag_router

app = FastAPI(title="Havruta AI Tutor API")

app.include_router(rag_router, prefix="/rag", tags=["rag"])


@app.get("/")
def health_check():
    return {"message": "Havruta AI Tutor API is running"}
