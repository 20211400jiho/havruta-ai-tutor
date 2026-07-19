from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database.database import Base


class Room(Base):
    # 데이터베이스 테이블 이름
    __tablename__ = "rooms"

    # 학습방 번호
    room_id = Column(Integer, primary_key=True, index=True)

    # 학습방 제목
    title = Column(String(100), nullable=False)

    # 초대 코드
    invite_code = Column(String(10), unique=True, index=True, nullable=False)

    # 방 생성자
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 최대 참여 인원
    max_members = Column(Integer, default=2, nullable=False)

    # 생성 시간
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)