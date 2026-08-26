from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class Recordatorios(Base):
    """Recordatorios persistidos cuando el Conversador ejecuta agendar_recordatorio (KB Antonia)."""

    __tablename__ = "recordatorios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dia: Mapped[str] = mapped_column(String, nullable=False)
    hora: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
