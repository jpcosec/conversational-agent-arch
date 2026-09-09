from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class Consultas(Base):
    """Consultas derivadas por el agente (KB Antonia): ticket MedInfo o reporte de
    evento adverso para farmacovigilancia. Lo persiste la tool ``registrar_consulta``.

    Antes no existia: el step decia "registrar un ticket MedInfo" y el Conversador
    afirmaba haberlo hecho sin que quedara nada; el gate lo rechazaba como accion
    no ejecutada y la persona recibia el handoff generico.
    """

    __tablename__ = "consultas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    #: ``medinfo`` (consulta medica del programa) o ``evento_adverso`` (farmacovigilancia).
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    #: Texto textual de lo que dijo la persona: farmacovigilancia exige el verbatim.
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    urgente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="abierta")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
