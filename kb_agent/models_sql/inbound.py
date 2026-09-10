from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class InboundStatus(str, Enum):
    """Ciclo de vida de un mensaje entrante de un proveedor externo.

    * ``received`` -- persistido, el turno todavia no corrio (o esta corriendo).
    * ``replied``  -- el turno corrio y ``reply_text`` es lo que se devolvio.
    * ``failed``   -- el turno revento; queda el mensaje para no perderlo.
    """

    RECEIVED = "received"
    REPLIED = "replied"
    FAILED = "failed"


class InboundMessage(Base):
    """Un mensaje que entro por un canal externo (Twilio WhatsApp/SMS, ...).

    Es la fuente ("source") de cada turno que no nace en la UI: guarda de que
    proveedor vino, con que id externo, por que canal, el payload crudo y a
    que usuario y turno dio origen. Dos cosas que sin esta tabla no existian:

    * **Idempotencia.** Twilio reintenta el webhook si no recibe respuesta a
      tiempo (15 s). ``(provider, provider_message_id)`` es UNIQUE: un reintento
      no corre el turno de nuevo, devuelve la respuesta ya guardada.
    * **Trazabilidad.** Desde un turno se llega al mensaje del proveedor que lo
      origino (``turn_id``), y desde el mensaje al usuario (``user_id``) que el
      orquestador resolvio (unificado por telefono si ``identity_key='phone'``).
    """

    __tablename__ = "inbound_messages"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_message_id", name="uq_inbound_messages_provider_message_id"
        ),
        Index("ix_inbound_messages_user_id_created_at", "user_id", "created_at"),
        Index("ix_inbound_messages_external_id", "external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Proveedor que entrego el mensaje (``twilio``).
    provider: Mapped[str] = mapped_column(String, nullable=False)
    #: Id del mensaje en el proveedor (Twilio ``MessageSid``). Nullable por si
    #: un proveedor no lo manda; en ese caso no hay idempotencia para esa fila.
    provider_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Canal normalizado (``whatsapp``/``sms``/...), el mismo que ``users.channel``.
    channel: Mapped[str] = mapped_column(String, nullable=False)
    #: ``external_id`` normalizado con el que se resolvio el usuario
    #: (``whatsapp:+569...``, ``sms:+569...``).
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    #: Telefono canonico del remitente (``+569...``) si el canal lo aporta.
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Destino tal como lo mando el proveedor (nuestro numero/sender).
    to: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: Nombre de perfil que aporta el canal (WhatsApp ``ProfileName``).
    profile_name: Mapped[str | None] = mapped_column(String, nullable=True)
    num_media: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Payload crudo del webhook, para auditoria y para campos que hoy no se usan.
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    #: ``turns.turn_id`` del turno que origino (no FK: turn_id no es unico global).
    turn_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Id en el proveedor del mensaje saliente con la respuesta (modo async:
    #: la respuesta sale por REST, no por TwiML). None en modo sync.
    reply_provider_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[InboundStatus] = mapped_column(
        SqlEnum(InboundStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=InboundStatus.RECEIVED,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
