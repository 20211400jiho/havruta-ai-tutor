from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    room_id: int
    topic: str = Field(default="직선의 방정식", min_length=1, max_length=255)


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)
