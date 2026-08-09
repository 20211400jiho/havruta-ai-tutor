from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.database import Base


class ChatState(str, Enum):
    STARTED = "started"
    QUESTIONING = "questioning"
    ANSWERED = "answered"
    FEEDBACK = "feedback"
    FINISHED = "finished"


class SenderType(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    # 채팅 세션 고유 번호
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    # 학습방 번호
    room_id: Mapped[int] = mapped_column(
        ForeignKey("learning_rooms.id"),
        nullable=False
    )

    # 사용자 번호
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    # 학습 주제
    topic: Mapped[str | None] = mapped_column(
        String(255)
    )

    # 현재 채팅 진행 상태
    state: Mapped[str] = mapped_column(
        String(50),
        default=ChatState.STARTED.value,
        nullable=False
    )

    # 채팅 시작 시간
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    # 채팅 종료 시간
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    # 학습방과 연결
    room = relationship(
        "LearningRoom",
        back_populates="chat_sessions"
    )

    # 사용자와 연결
    user = relationship(
        "User",
        back_populates="chat_sessions"
    )

    # 해당 세션에서 주고받은 메시지
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    # 해당 세션의 학습 기록
    learning_record = relationship(
        "LearningRecord",
        back_populates="session",
        uselist=False
    )


class Message(Base):
    __tablename__ = "messages"

    # 메시지 고유 번호
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    # 채팅 세션 번호
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"),
        nullable=False
    )

    # 메시지를 보낸 주체
    # user / ai / system
    sender_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    # 실제 메시지 내용
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 메시지 생성 시간
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    # 채팅 세션과 연결
    session = relationship(
        "ChatSession",
        back_populates="messages"
    )