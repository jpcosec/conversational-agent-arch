from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base


class TurnKind(str, Enum):
    """Autoria de un turno (decision del owner).

    * ``user`` -- lo dijo la persona.
    * ``agent`` -- lo genero nuestro agente; guarda el trail completo
      (decision, bundle, gate, tool) para auditar de donde salio la respuesta.
    * ``override`` -- lo dijo un humano de nuestro lado (takeover), no el
      agente. Aun no hay UI de takeover; el tipo queda modelado para cuando la
      haya, y para no tener que migrar despues.
    """

    USER = "user"
    AGENT = "agent"
    OVERRIDE = "override"


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
        Index("ix_turns_conversation_id_created_at", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turn_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    #: Conversacion a la que pertenece el turno. Nullable por compatibilidad
    #: con filas viejas (pre-migracion); el runtime siempre lo setea.
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    #: Autoria del turno (user/agent/override). Default agent: hasta ahora la
    #: tabla solo guardaba turnos del agente (con su trail).
    #: ``values_callable``: se persiste el VALOR del enum ("agent"), no su
    #: nombre ("AGENT"). Es lo que ya escribio la migracion que creo la
    #: columna (``server_default="agent"``, c1a2b3d4e5f6), asi que sin esto
    #: toda fila anterior a esa migracion -- o insertada por el default del
    #: motor -- era ilegible para el ORM: "LookupError: 'agent' is not among
    #: the defined enum values" al abrir el Turn Inspector o /api/metrics
    #: sobre la base de produccion. La migracion e5f6a7b8c9d1 normaliza las
    #: filas que si quedaron con el nombre.
    kind: Mapped[TurnKind] = mapped_column(
        SqlEnum(
            TurnKind,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=TurnKind.AGENT,
    )
    step_before: Mapped[str | None] = mapped_column(String, nullable=True)
    step_after: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    draft: Mapped[str] = mapped_column(Text, nullable=False)
    gate: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    bundle: Mapped[list[object]] = mapped_column(JSON, nullable=False)
    tool: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    #: Cuanto tardo el turno completo, en milisegundos (compilar contexto ->
    #: orquestador -> conversador -> gate). Es la unica fuente honesta de
    #: latencia: ``created_at`` de las dos filas de ``chat_history`` de un
    #: turno se escribe en el mismo commit, asi que su diferencia es cero.
    #: ``None`` en filas anteriores a la migracion ``e5f6a7b8c9d0``.
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
