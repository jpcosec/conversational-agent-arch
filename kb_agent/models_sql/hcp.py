"""Recontactos y consentimientos del piloto HCP (``knowledge_hcp``).

Dos tablas planas que persisten las tools ``programar_recontacto`` y
``actualizar_consentimiento`` declaradas por los ToolAtom de la KB HCP. El
``hcp_id`` que el modelo pasa en los args NO se guarda: la identidad del
medico es ``users.id`` (ver ``kb_agent/tools/hcp.py``).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class Recontactos(Base):
    """Recontacto agendado cuando el Conversador ejecuta ``programar_recontacto``."""

    __tablename__ = "recontactos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    fecha_recontacto: Mapped[str] = mapped_column(String, nullable=False)
    #: manana | tarde | noche (enum del ToolAtom); texto libre a proposito.
    franja_horaria: Mapped[str | None] = mapped_column(String, nullable=True)
    campania_id: Mapped[str | None] = mapped_column(String, nullable=True)
    nota_contexto: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Consentimientos(Base):
    """Decision de consentimiento registrada por ``actualizar_consentimiento``."""

    __tablename__ = "consentimientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    #: opt_in | active_contact | campaign_opt_out | channel_opt_out | dsr_erasure_requested
    nuevo_estado: Mapped[str] = mapped_column(String, nullable=False)
    campania_id: Mapped[str | None] = mapped_column(String, nullable=True)
    motivo_verbatim: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
