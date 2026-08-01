from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


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

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("learning_rooms.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(50), default=ChatState.STARTED.value, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    room = relationship("LearningRoom", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    feedbacks = relationship("AIFeedback", back_populates="session", cascade="all, delete-orphan")
    learning_record = relationship("LearningRecord", back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    feedbacks = relationship("AIFeedback", back_populates="message")
    rag_references = relationship("RagReference", back_populates="message", cascade="all, delete-orphan")


class RoomChatMessage(Base):
    __tablename__ = "room_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("learning_rooms.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User")
    room = relationship("LearningRoom")
