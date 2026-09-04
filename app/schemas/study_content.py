from pydantic import BaseModel, Field


class QuizGenerateRequest(BaseModel):
    topic: str = Field(default="직선의 방정식", min_length=1, max_length=255)
    subject: str | None = Field(default=None, min_length=1, max_length=100)
    unit_code: str | None = Field(default=None, min_length=1, max_length=100)
    school_level: str | None = Field(default=None, min_length=1, max_length=50)
    grade: str | None = Field(default=None, min_length=1, max_length=50)
    question_count: int = Field(default=3, ge=1, le=10)


class QuizSubmitRequest(BaseModel):
    answers: list[int]
