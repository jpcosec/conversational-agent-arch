"""Info basica del lead y sus visitas solicitadas (negocios de venta con agendamiento).

Dos tablas planas, sin semantica de negocio: ``leads`` (una fila por
``users.id``: quien es la persona y que dijo de si misma) y ``visitas`` (cada
reunion que pidio, con la preferencia de horario tal como la expreso). La
semantica -- que campo pisa a cual, que falta para agendar, que significa
"solicitada" -- vive en los handlers de ``kb_agent/tools/leads.py`` y
``kb_agent/tools/visitas.py``, que son las tools que ve el agente.

PII (decision deliberada): a diferencia de ``registrar_enrolamiento``, aca
nombre, email y telefono SI se persisten, porque el proposito declarado por
la KB es que el equipo comercial confirme la visita por esos medios. Lo que
NO se hace es dejarlos en claro en ``turns.tool`` (ver los handlers).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class Leads(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    #: suite | broker | franquicia (segmentos de la KB); texto libre a proposito.
    segmento: Mapped[str | None] = mapped_column(String, nullable=True)
    #: para mi | un familiar | inversion
    para_quien: Mapped[str | None] = mapped_column(String, nullable=True)
    edad_rango: Mapped[str | None] = mapped_column(String, nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String, nullable=True)
    pais: Mapped[str | None] = mapped_column(String, nullable=True)
    proposito: Mapped[str | None] = mapped_column(String, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    #: Campos que una tool puede escribir. Fuente unica para el upsert parcial.
    EDITABLE_FIELDS = (
        "nombre", "email", "telefono", "segmento", "para_quien",
        "edad_rango", "ciudad", "pais", "proposito", "notas",
    )


class VisitaEstado(str, Enum):
    SOLICITADA = "solicitada"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"


class Visitas(Base):
    __tablename__ = "visitas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    #: presencial | videollamada
    modalidad: Mapped[str] = mapped_column(String, nullable=False)
    #: Preferencia de dia y bloque TAL COMO la dijo la persona ("jueves en la
    #: tarde"). No es una fecha: el equipo la convierte en hora concreta.
    preferencia: Mapped[str] = mapped_column(String, nullable=False)
    titulo: Mapped[str | None] = mapped_column(String, nullable=True)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    estado: Mapped[str] = mapped_column(String, nullable=False, default=VisitaEstado.SOLICITADA.value)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
