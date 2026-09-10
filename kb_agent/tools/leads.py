"""Tool ``registrar_lead``: wrapper semantico sobre la tabla plana ``leads``.

Se registra desde el yaml del negocio::

    tools:
      registrar_lead: kb_agent.tools.leads:registrar_lead

Que hace de "semantico"
-----------------------
- **Upsert parcial**: solo pisa los campos que vienen informados; lo que la
  persona dijo antes se conserva (puede corregirse dando el valor de nuevo).
- **Completa con lo ya capturado**: el orquestador guarda en
  ``session_state.flow_slots["collected"]`` los datos que detecto en los
  mensajes crudos (email, telefono, preferencia, modalidad -- ver
  ``kb_agent/lead_slots.py``). Si el modelo no los paso como argumento, el
  handler los toma de ahi: la tool no depende de que el LLM re-extraiga un
  email del historial.
- **Devuelve estado, no filas**: que campos quedaron conocidos y que falta
  para poder agendar, para que el Conversador pida SOLO lo que falta.

PII en el rastro: el resultado incluye una clave ``args`` propia con
booleanos "vino informado" que pisa a los args crudos que ``execute_tool``
pone en ``turns.tool`` (mismo patron que ``registrar_enrolamiento``). Los
valores SI se persisten en ``leads`` (proposito declarado por la KB).
"""
from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.orm import Session

from kb_agent.models_sql.leads import Leads
from kb_agent.models_sql.session import SessionState

#: Campos con PII: en el rastro del turno solo se informa si vinieron.
PII_FIELDS = ("nombre", "email", "telefono")

#: Sin estos no hay visita que crear (ver ``kb_agent/tools/visitas.py``).
REQUIRED_FOR_VISIT = ("modalidad", "preferencia", "email", "telefono")

#: slot capturado por el orquestador -> campo del lead / de la visita.
_COLLECTED_TO_FIELD = {
    "email": "email",
    "telefono": "telefono",
    "modalidad": "modalidad",
    "preferencia_visita": "preferencia",
}

_PRESENCIAL = ("presencial", "oficina", "en persona", "visita")
_VIDEO = ("video", "virtual", "online", "remot", "zoom", "meet")


def clean(value: Any) -> str | None:
    """Texto normalizado o None si viene vacio."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_modalidad(value: Any) -> str | None:
    text = clean(value)
    if text is None:
        return None
    folded = text.lower()
    if any(k in folded for k in _VIDEO):
        return "videollamada"
    if any(k in folded for k in _PRESENCIAL):
        return "presencial"
    return folded


def collected_slots(session: Session, user_id: int | None) -> dict[str, Any]:
    """Slots capturados por el orquestador (``flow_slots.collected``) mapeados a campos."""
    if user_id is None:
        return {}
    state = session.get(SessionState, user_id)
    slots = state.flow_slots if state is not None and isinstance(state.flow_slots, dict) else {}
    collected = slots.get("collected") or {}
    if not isinstance(collected, Mapping):
        return {}
    return {field: collected[slot] for slot, field in _COLLECTED_TO_FIELD.items() if clean(collected.get(slot))}


def merge_with_collected(session: Session, user_id: int | None, args: Mapping[str, Any]) -> dict[str, Any]:
    """Args del modelo sobre lo capturado: lo explicito gana, lo capturado completa."""
    merged = dict(collected_slots(session, user_id))
    merged.update({k: v for k, v in args.items() if clean(v) is not None})
    if "modalidad" in merged:
        merged["modalidad"] = normalize_modalidad(merged["modalidad"])
    return merged


def upsert_lead(session: Session, user_id: int, data: Mapping[str, Any]) -> tuple[Leads, list[str]]:
    """Crea o actualiza la fila del lead con los campos informados. Devuelve (lead, campos cambiados)."""
    lead = session.query(Leads).filter(Leads.user_id == user_id).one_or_none()
    if lead is None:
        lead = Leads(user_id=user_id)
        session.add(lead)
    changed: list[str] = []
    for field in Leads.EDITABLE_FIELDS:
        value = clean(data.get(field))
        if value is None or getattr(lead, field) == value:
            continue
        setattr(lead, field, value)
        changed.append(field)
    session.flush()
    return lead, changed


def lead_status(lead: Leads | None) -> dict[str, Any]:
    """Que se sabe del lead, sin exponer PII: los campos PII salen como booleanos."""
    if lead is None:
        return {"conocido": {}, "falta_contacto": ["email", "telefono"]}
    conocido: dict[str, Any] = {}
    for field in Leads.EDITABLE_FIELDS:
        value = getattr(lead, field)
        if field in PII_FIELDS:
            conocido[f"{field}_registrado"] = bool(value)
        elif value:
            conocido[field] = value
    return {
        "conocido": conocido,
        "falta_contacto": [f for f in ("email", "telefono") if not getattr(lead, f)],
    }


def redacted_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """Para ``turns.tool``: PII como "vino informado", el resto en claro."""
    out: dict[str, Any] = {}
    for key, value in args.items():
        if key in PII_FIELDS:
            out[f"{key}_provisto"] = clean(value) is not None
        else:
            out[key] = value
    return out


def registrar_lead(session: Session, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
    if user_id is None:
        return {"status": "sin_usuario", "args": redacted_args(args)}
    data = merge_with_collected(session, user_id, args)
    lead, changed = upsert_lead(session, user_id, data)
    session.commit()
    return {
        "lead_id": lead.id,
        "campos_actualizados": changed,
        **lead_status(lead),
        "args": redacted_args(args),
    }
