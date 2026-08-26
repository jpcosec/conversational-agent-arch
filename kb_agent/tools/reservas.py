"""Handler de la tool ``crear_reserva`` (negocios con reserva de mesa).

Se registra desde ``project.config.yaml``::

    tools:
      crear_reserva: kb_agent.tools.reservas:crear_reserva
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kb_agent.models_sql.reservas import Reservas


def crear_reserva(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    reserva = Reservas(
        user_id=user_id,
        fecha=str(args.get("fecha", "")),
        hora=str(args.get("hora", "")),
        personas=int(args.get("personas", 0)),
        nombre=args.get("nombre"),
    )
    session.add(reserva)
    session.commit()
    return {"reserva_id": reserva.id}
