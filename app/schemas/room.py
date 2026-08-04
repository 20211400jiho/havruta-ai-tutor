from pydantic import BaseModel, Field


# 학습방 생성 요청 데이터
class RoomCreateRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["수학 하브루타 학습방"]
    )
    subject: str | None = Field(default="수학", max_length=100)
    grade: str | None = Field(default="고등학교 1학년", max_length=50)
    max_members: int = Field(
        default=2,
        ge=2,
        le=10,
        examples=[2]
    )


# 학습방 참여 요청 데이터
class RoomJoinRequest(BaseModel):
    invite_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        examples=["A1B2C3"]
    )
