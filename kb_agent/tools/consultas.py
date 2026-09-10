"""Handler de la tool ``registrar_consulta`` (KB Antonia — PSP Selfix).

Se registra desde ``project.config.yaml``::

    tools:
      registrar_consulta: kb_agent.tools.consultas:registrar_consulta

Persiste en ``consultas`` un ticket MedInfo (``tipo: medinfo``) o un reporte de
evento adverso para farmacovigilancia (``tipo: evento_adverso``) con el texto
textual de la persona. Devuelve el id y el tipo; en ``args`` devuelve solo
booleanos de "vino informado" (mismo patron que ``registrar_enrolamiento``)
para que el texto clinico no quede duplicado en claro en ``turns.tool``.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kb_agent.models_sql.consultas import Consultas

TIPOS = ("medinfo", "evento_adverso")


def registrar_consulta(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    tipo = str(args.get("tipo") or "medinfo").strip().lower()
    if tipo not in TIPOS:
        return {"status": "error", "error": f"tipo invalido: {tipo!r}; usar uno de {list(TIPOS)}"}
    texto = str(args.get("texto") or "").strip()
    if not texto:
        return {"status": "error", "error": "falta 'texto': la consulta o el evento tal como lo dijo la persona"}
    urgente = bool(args.get("urgente")) if not isinstance(args.get("urgente"), str) else args["urgente"].strip().lower() in {"si", "sí", "true", "1"}
    row = Consultas(user_id=user_id, tipo=tipo, texto=texto, urgente=urgente)
    session.add(row)
    session.commit()
    return {
        "consulta_id": row.id,
        "tipo": tipo,
        "urgente": urgente,
        "estado": row.estado,
        "args": {"tipo": tipo, "texto_informado": True, "urgente": urgente},
    }
