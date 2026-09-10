"""Handlers de las tools del piloto HCP (KB ``knowledge_hcp``).

Se registran desde ``project.config.yaml``::

    tools:
      programar_recontacto: kb_agent.tools.hcp:programar_recontacto
      actualizar_consentimiento: kb_agent.tools.hcp:actualizar_consentimiento

El ``hcp_id`` de los args se ignora: la identidad del medico es el
``user_id`` que resuelve el orquestador (``users.id``).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kb_agent.models_sql.hcp import Consentimientos, Recontactos


def programar_recontacto(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    """Persiste el recontacto pedido por el medico (fecha, franja, campana que se retoma)."""
    recontacto = Recontactos(
        user_id=user_id,
        fecha_recontacto=str(args.get("fecha_recontacto", "")),
        franja_horaria=args.get("franja_horaria"),
        campania_id=args.get("campania_id"),
        nota_contexto=args.get("nota_contexto"),
    )
    session.add(recontacto)
    session.commit()
    return {"recontacto_id": recontacto.id}


def actualizar_consentimiento(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    """Persiste la decision de consentimiento del medico con su motivo textual."""
    consentimiento = Consentimientos(
        user_id=user_id,
        nuevo_estado=str(args.get("nuevo_estado", "")),
        campania_id=args.get("campania_id"),
        motivo_verbatim=args.get("motivo_verbatim"),
    )
    session.add(consentimiento)
    session.commit()
    return {"consentimiento_id": consentimiento.id}
