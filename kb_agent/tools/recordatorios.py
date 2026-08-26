"""Handler de la tool ``agendar_recordatorio`` (KB Antonia — PSP Selfix).

Se registra desde ``project.config.yaml``::

    tools:
      agendar_recordatorio: kb_agent.tools.recordatorios:agendar_recordatorio
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kb_agent.models_sql.recordatorios import Recordatorios


def agendar_recordatorio(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    recordatorio = Recordatorios(
        user_id=user_id,
        dia=str(args.get("dia", "")),
        hora=str(args.get("hora", "")),
        nombre=args.get("nombre"),
    )
    session.add(recordatorio)
    session.commit()
    return {"recordatorio_id": recordatorio.id}
