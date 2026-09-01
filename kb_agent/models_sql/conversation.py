from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .identity import Base


class ConversationStatus(str, Enum):
    """Estado de vida de una conversacion.

    ``open`` mientras recibe turnos; ``closed`` cuando el criterio de cierre
    (inactividad, ver ``ProjectConfig.conversation_idle_ttl_s``) la termina. El
    historial que va al prompt no cruza el limite de una conversacion cerrada.
    """

    OPEN = "open"
    CLOSED = "closed"


class Conversation(Base):
    """Una conversacion: la unidad que agrupa los turnos de un usuario en un
    tramo temporal acotado.

    El owner decidio el modelo: un Usuario tiene una LISTA de conversaciones;
    una Conversacion es una lista de turnos; el historial que se inyecta al
    prompt no debe cruzar el limite de la conversacion. Antes esta entidad no
    existia: el sistema infería "conversacion" por dia calendario
    (``frontends/chat/app.py::_group_conversations``) y el historial se
    filtraba solo por ``user_id``, mezclando conversaciones distintas.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_id_status", "user_id", "status"),
        Index("ix_conversations_user_id_last_activity", "user_id", "last_activity_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(
        SqlEnum(ConversationStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=ConversationStatus.OPEN,
    )
    #: Canal por el que arranco la conversacion (whatsapp/web/ui). El mismo
    #: usuario puede tener conversaciones en canales distintos.
    channel: Mapped[str | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    #: Se actualiza en cada turno; base del criterio de cierre por inactividad.
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("Users")
