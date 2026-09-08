"""Tool ``crear_visita``: wrapper semantico sobre la tabla plana ``visitas``.

Se registra desde el yaml del negocio::

    tools:
      crear_visita: kb_agent.tools.visitas:crear_visita

Semantica
---------
- Una visita nace ``solicitada``: la KB dice que el agente NO ve la agenda y
  el equipo comercial confirma la hora. Por eso ``preferencia`` es el texto
  que dijo la persona ("jueves en la tarde"), no una fecha.
- Crear la visita implica registrar el contacto: email/telefono/nombre que
  vengan (como argumento o capturados en la conversacion) se guardan en
  ``leads`` via ``upsert_lead`` antes de crear la fila.
- Si faltan datos minimos (modalidad, preferencia, email, telefono) NO crea
  nada y devuelve ``status: faltan_datos`` con la lista, para que el
  Conversador los pida en vez de afirmar que agendo.
- Idempotencia suave: si el lead ya tiene una visita ``solicitada`` con la
  misma modalidad y preferencia, la devuelve en vez de duplicarla.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from kb_agent.models_sql.leads import VisitaEstado, Visitas
from kb_agent.tools.leads import (
    REQUIRED_FOR_VISIT,
    clean,
    lead_status,
    merge_with_collected,
    redacted_args,
    upsert_lead,
)

DEFAULT_DURACION_MIN = 30


def crear_visita(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    if user_id is None:
        return {"status": "sin_usuario", "args": redacted_args(args)}

    data = merge_with_collected(session, user_id, args)
    # El contacto (y lo demas que venga del lead) se registra aunque la
    # visita no se pueda crear todavia: lo dicho no se pierde.
    lead, changed = upsert_lead(session, user_id, data)
    # El lead ya registrado en turnos previos completa lo que el modelo no paso.
    for field in ("email", "telefono"):
        if clean(data.get(field)) is None and getattr(lead, field):
            data[field] = getattr(lead, field)

    faltan = [f for f in REQUIRED_FOR_VISIT if clean(data.get(f)) is None]
    if faltan:
        session.commit()
        return {
            "status": "faltan_datos",
            "faltan": faltan,
            "lead_id": lead.id,
            "campos_actualizados": changed,
            **lead_status(lead),
            "args": redacted_args(args),
        }

    modalidad = str(data["modalidad"])
    preferencia = str(clean(data["preferencia"]))
    existente = (
        session.query(Visitas)
        .filter(
            Visitas.user_id == user_id,
            Visitas.estado == VisitaEstado.SOLICITADA.value,
            Visitas.modalidad == modalidad,
            Visitas.preferencia == preferencia,
        )
        .order_by(Visitas.id.desc())
        .first()
    )
    if existente is not None:
        visita = existente
        creada = False
    else:
        visita = Visitas(
            user_id=user_id,
            lead_id=lead.id,
            modalidad=modalidad,
            preferencia=preferencia,
            titulo=clean(data.get("titulo")) or clean(data.get("proposito")) or lead.proposito,
            duracion_min=int(data.get("duracion_min") or DEFAULT_DURACION_MIN),
            estado=VisitaEstado.SOLICITADA.value,
            notas=clean(data.get("notas")),
        )
        session.add(visita)
        creada = True
    session.commit()
    return {
        "visita_id": visita.id,
        "creada": creada,
        "estado": visita.estado,
        "modalidad": visita.modalidad,
        "preferencia": visita.preferencia,
        "titulo": visita.titulo,
        "duracion_min": visita.duracion_min,
        "lead_id": lead.id,
        "campos_actualizados": changed,
        **lead_status(lead),
        "args": redacted_args(args),
    }
