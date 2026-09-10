"""Datos del lead capturados del mensaje CRUDO del turno, antes del scrub PII.

``chat_history`` se persiste scrubbeado (``kb_agent.pii.scrubber.scrub``): un
email o un telefono que el cliente escribio quedan como ``<EMAIL_1>`` /
``<PHONE_1>`` y no se pueden recuperar despues. Pero agendar una visita
NECESITA esos datos (la invitacion sale al correo, el equipo confirma por
telefono), asi que el orquestador los captura aca, de forma determinista
(regex, sin LLM), y los guarda en ``session_state.flow_slots["collected"]``.
Es la unica copia sin scrub y existe solo para el proposito declarado por la
KB (datos de contacto de la cita).

Slots capturados (todos opcionales, solo se escribe lo que aparece):

- ``email``               -- primer email del mensaje.
- ``telefono``            -- primer telefono (>= 8 digitos), normalizado sin
                             espacios ni guiones.
- ``preferencia_visita``  -- dia (lunes..domingo, hoy, manana, esta/proxima
                             semana) + bloque (manana/tarde/noche) + hora
                             explicita si la dio, en texto legible.
- ``modalidad``           -- "presencial" o "videollamada".

``merge_lead_slots`` conserva lo ya capturado en turnos previos y deja que un
valor nuevo lo reemplace (el cliente puede corregir su correo).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\+?\d[\d\s.\-()]{6,18}\d")
_DAYS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
_DAY_LABEL = {"miercoles": "miércoles", "sabado": "sábado"}
_RELATIVE = (
    ("pasado manana", "pasado mañana"),
    ("esta semana", "esta semana"),
    ("la proxima semana", "la próxima semana"),
    ("proxima semana", "la próxima semana"),
    ("la otra semana", "la otra semana"),
    ("hoy", "hoy"),
)
_BLOCK_MORNING = re.compile(r"\b(?:en|por|de) la manana\b|\ben la mañana\b|\bam\b")
_BLOCK = (
    ("mediodia", "al mediodía"),
    ("tarde", "en la tarde"),
    ("noche", "en la noche"),
)
_HOUR = re.compile(r"\b(?:a las\s+)?((?:[01]?\d|2[0-3])(?::[0-5]\d)?)\s*(?:hrs?\b|h\b|horas\b|am\b|pm\b)|\ba las\s+((?:[01]?\d|2[0-3])(?::[0-5]\d)?)\b")
_PRESENCIAL = re.compile(r"\bpresencial\b|\ben persona\b|\ben la oficina\b|\bir a la oficina\b|\bvisitar(?:los|la|lo)?\b")
_VIDEO = re.compile(r"\bvideo\s*llamada\b|\bvirtual\b|\bonline\b|\bzoom\b|\bmeet\b|\bremot[oa]\b|\bpor llamada\b")


def _fold(text: str) -> str:
    """minusculas sin acentos, para matchear 'miércoles' y 'miercoles' igual."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _phone(text: str) -> str | None:
    for m in _PHONE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 8 <= len(digits) <= 15:
            return ("+" if m.group(0).strip().startswith("+") else "") + digits
    return None


def _visit_preference(folded: str, raw: str) -> str | None:
    parts: list[str] = []
    days = [d for d in _DAYS if re.search(rf"\b{d}\b", folded)]
    parts.extend(_DAY_LABEL.get(d, d) for d in days)
    morning_block = bool(_BLOCK_MORNING.search(folded))
    for key, label in _RELATIVE:
        if re.search(rf"\b{key}\b", folded):
            parts.append(label)
            break
    else:
        # 'manana' pelado = el dia de manana; '(en|por|de) la manana' = bloque.
        # Se quita el bloque antes de buscar el dia: 'manana en la manana' trae ambos.
        if re.search(r"\bmanana\b", _BLOCK_MORNING.sub(" ", folded)):
            parts.append("mañana")
    block = "en la mañana" if morning_block else None
    if block is None:
        for key, label in _BLOCK:
            if re.search(rf"\b{key}\b", folded):
                block = label
                break
    if block:
        parts.append(block)
    hour = _HOUR.search(folded)
    if hour:
        value = hour.group(1) or hour.group(2)
        if value:
            parts.append(f"a las {value}")
    return " ".join(parts) if parts else None


def extract_lead_slots(message: str) -> dict[str, str]:
    """Slots presentes en ``message`` (solo los encontrados)."""
    if not message or not message.strip():
        return {}
    folded = _fold(message)
    out: dict[str, str] = {}
    email = _EMAIL.search(message)
    if email:
        out["email"] = email.group(0)
    # el telefono se busca sobre el texto sin el email (un email puede traer digitos)
    phone = _phone(_EMAIL.sub(" ", message))
    if phone:
        out["telefono"] = phone
    pref = _visit_preference(folded, message)
    if pref:
        out["preferencia_visita"] = pref
    if _PRESENCIAL.search(folded):
        out["modalidad"] = "presencial"
    elif _VIDEO.search(folded):
        out["modalidad"] = "videollamada"
    return out


def merge_lead_slots(previous: Mapping[str, Any] | None, found: Mapping[str, str]) -> dict[str, Any]:
    """Lo previo se conserva; lo nuevo reemplaza (el cliente puede corregirse)."""
    merged: dict[str, Any] = dict(previous or {})
    merged.update({k: v for k, v in found.items() if v})
    return merged
