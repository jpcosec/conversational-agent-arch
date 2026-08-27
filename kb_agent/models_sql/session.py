from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class SessionNode(str, Enum):
    IDLE = "idle"
    BUFFERING = "buffering"
    EVALUATING_CONTEXT = "evaluating_context"
    DRAFTING_RESPONSE = "drafting_response"
    WAITING_TOOL = "waiting_tool"
    BREAKPOINT_MISS = "breakpoint_miss"


class SessionState(Base):
    __tablename__ = "session_state"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current_node: Mapped[SessionNode] = mapped_column(
        SqlEnum(SessionNode, native_enum=False, validate_strings=True),
        nullable=False,
        default=SessionNode.IDLE,
    )
    active_domain: Mapped[str | None] = mapped_column(String, nullable=True)
    flow_node: Mapped[str | None] = mapped_column(String, nullable=True)
    flow_slots: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    buffer: Mapped[dict[str, list[object]]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"debounce": [], "tool_wait": []},
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = (
        Index("ix_chat_history_user_id_created_at", "user_id", "created_at"),
        Index("ix_chat_history_user_id_session_id", "user_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(
        SqlEnum("user", "assistant", "system", name="chat_history_role", native_enum=False, validate_strings=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    pii_scrubbed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
