from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


# 사용자 정보를 저장하는 테이블
class User(Base):
    __tablename__ = "users"

    # 사용자 고유 번호
    id = Column(Integer, primary_key=True, index=True)

    # 로그인에 사용할 이메일
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # 암호화된 비밀번호
    password = Column(
        String(255),
        nullable=False
    )

    # 사용자 이름
    name = Column(
        String(50),
        nullable=False
    )

    # 학년
    grade = Column(
        Integer,
        nullable=False
    )

    # 사용자가 생성한 학습방
    owned_rooms = relationship(
        "LearningRoom",
        back_populates="owner"
    )

    # 사용자가 참여한 학습방
    room_memberships = relationship(
        "RoomMember",
        back_populates="user"
    )

    # 사용자의 채팅 세션
    chat_sessions = relationship(
        "ChatSession",
        back_populates="user"
    )

    # 사용자의 학습 기록
    learning_records = relationship(
        "LearningRecord",
        back_populates="user"
    )