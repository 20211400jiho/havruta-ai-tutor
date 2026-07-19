from pydantic import BaseModel, Field


# 학습방 생성 요청 데이터
class RoomCreateRequest(BaseModel):
    # 학습방 제목
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["수학 하브루타 학습방"]
    )

    # 학습방 최대 참여 인원
    max_members: int = Field(
        default=2,
        ge=2,
        le=10,
        examples=[2]
    )


# 학습방 참여 요청 데이터
class RoomJoinRequest(BaseModel):
    # 참여할 학습방의 초대 코드
    invite_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        examples=["A1B2C3"]
    )