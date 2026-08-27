from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class Turns(Base):
    """Rastro auditable de un turno: decision del orquestador, bundle de contexto
    que entro al prompt, borrador del conversador ANTES del gate, veredicto del
    gate y (si hubo) la tool invocada con su resultado.

    ``turn_id`` es el id que hoy genera el runtime (p.ej. "t1", "t2", ...) pero
    ese contador es por-sesion (ver frontends/chat/app.py, dict `counters`
    indexado por session_id) y por lo tanto NO es globalmente unico: dos
    sesiones distintas pueden generar el mismo "t1". Por eso la PK real es un
    ``id`` autoincremental -- igual que chat_history/reservas/recordatorios --
    y ``turn_id`` queda como columna de negocio, unica solo dentro de su
    sesion (UniqueConstraint sobre session_id+turn_id). Esto evita atarse hoy
    a que el runtime empiece a emitir uuids, sin perder la capacidad de buscar
    un turno puntual por (session_id, turn_id) para el Turn Inspector.
    """

    __tablename__ = "turns"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_id", name="uq_turns_session_id_turn_id"),
        Index("ix_turns_session_id_created_at", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turn_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    step_before: Mapped[str | None] = mapped_column(String, nullable=True)
    step_after: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    draft: Mapped[str] = mapped_column(Text, nullable=False)
    gate: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    bundle: Mapped[list[object]] = mapped_column(JSON, nullable=False)
    tool: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
