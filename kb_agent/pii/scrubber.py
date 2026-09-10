from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_agent.models_sql.session import ChatHistory

_PLACEHOLDER_PATTERN = re.compile(r"<(?P<kind>[A-Z_]+)_\d+>")
_EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_NATIONAL_ID_PATTERN = re.compile(
    r"\b(?:RUT|RUN|DNI|CI|CEDULA|CÉDULA|ID)\s*[:#-]?\s*[A-Z0-9.\-]{6,15}\b|\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b|\b\d{7,8}-[\dkK]\b",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(
    r"(?<!<)\b(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?(?:\d[\s.-]?){8,15}\d\b"
)
_ADDRESS_PATTERN = re.compile(
    r"\b(?:calle|cl\.?|avenida|av\.?|pasaje|psje\.?|camino|ruta|road|street|st\.?)\s+[A-ZÁÉÍÓÚÑ0-9][A-Za-zÁÉÍÓÚÑáéíóúñ0-9\s#.,-]{2,60}?\s+\d+[A-Za-z0-9-]*\b",
    re.IGNORECASE,
)
_NAME_PATTERN = re.compile(
    r"\b(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2})\b"
)

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", _EMAIL_PATTERN),
    ("CARD", _CARD_PATTERN),
    ("NATIONAL_ID", _NATIONAL_ID_PATTERN),
    ("PHONE", _PHONE_PATTERN),
    ("ADDRESS", _ADDRESS_PATTERN),
    ("NAME", _NAME_PATTERN),
)


class _PlaceholderRegistry:
    def __init__(self, text: str) -> None:
        self._seen: dict[str, dict[str, str]] = {kind: {} for kind, _ in _PATTERNS}
        self._counters: dict[str, int] = {kind: 0 for kind, _ in _PATTERNS}
        self._seed_from_placeholders(text)

    def _seed_from_placeholders(self, text: str) -> None:
        for match in _PLACEHOLDER_PATTERN.finditer(text):
            kind = match.group("kind")
            if kind in self._counters:
                index = int(match.group(0).rsplit("_", 1)[1][:-1])
                self._counters[kind] = max(self._counters[kind], index)

    def placeholder_for(self, kind: str, raw_value: str) -> str:
        normalized = raw_value.strip()
        cached = self._seen[kind].get(normalized)
        if cached is not None:
            return cached

        self._counters[kind] += 1
        placeholder = f"<{kind}_{self._counters[kind]}>"
        self._seen[kind][normalized] = placeholder
        return placeholder


#: Palabras que van con mayuscula solo por abrir la oracion y que el patron de
#: NAME tomaba como nombre propio ("Hola Carla", "Soy Antonia", "Gracias Pedro").
#: Se descartan del principio del match; lo que queda se evalua de nuevo.
_SENTENCE_STARTERS = frozenset({
    "hola", "soy", "gracias", "buenos", "buenas", "muchas", "entiendo", "claro", "perfecto",
    "que", "qué", "estoy", "para", "puedes", "recuerda", "cuéntame", "cuentame", "ya", "ok",
    "listo", "bien", "genial", "excelente", "ahora", "hoy", "chao", "chau", "adios", "adiós",
    "oye", "mira", "bueno", "dale", "vale", "si", "sí", "no", "me", "mi", "tu", "te",
})


def scrub(text: str, *, allowlist: Iterable[str] = ()) -> str:
    """Mask supported PII categories with stable placeholders.

    ``allowlist``: terminos que nunca son PII aunque parezcan un nombre (la marca,
    el nombre del asistente, el programa). Los declara el negocio en
    ``project.config.yaml`` (``pii_allowlist``); el runtime no sabe cuales son.
    """
    scrubbed = text
    registry = _PlaceholderRegistry(text)
    allowed = {a.strip().lower() for a in allowlist if a and a.strip()}
    for kind, pattern in _PATTERNS:
        if kind == "NAME":
            scrubbed = pattern.sub(lambda match: _replace_name(match, registry, allowed), scrubbed)
        else:
            scrubbed = pattern.sub(lambda match, pii_kind=kind: _replace(match, pii_kind, registry), scrubbed)
    return scrubbed


def _replace_name(match: re.Match[str], registry: _PlaceholderRegistry, allowed: set[str]) -> str:
    """Un match de NAME menos sus palabras de arranque y los terminos permitidos.

    "Hola Carla Rojas" -> "Hola <NAME_1>"; "Soy Antonia" -> intacto (arranque +
    una sola palabra); "Programa Selfix" permitido -> intacto; "Carla Rojas" ->
    "<NAME_1>". Un nombre solo (una palabra) nunca se enmascara: tampoco antes.
    """
    value = match.group(0)
    if value.startswith("<") and value.endswith(">"):
        return value
    if value.lower() in allowed:
        return value
    words = value.split()
    prefix: list[str] = []
    while words and (words[0].lower() in _SENTENCE_STARTERS or words[0].lower() in allowed):
        prefix.append(words.pop(0))
    if len(words) < 2 or any(w.lower() in allowed for w in words):
        return value
    head = (" ".join(prefix) + " ") if prefix else ""
    return head + registry.placeholder_for("NAME", " ".join(words))


def scrub_unscrubbed_chat_history(session: Session, *, batch_size: int = 100) -> int:
    """Rewrite pending chat history rows in place and mark them as scrubbed."""
    processed = 0

    while True:
        rows = list(_pending_rows(session, batch_size=batch_size))
        if not rows:
            break

        for row in rows:
            row.content = scrub(row.content)
            row.pii_scrubbed = True

        session.commit()
        processed += len(rows)

    return processed


def _pending_rows(session: Session, *, batch_size: int) -> Iterable[ChatHistory]:
    statement = (
        select(ChatHistory)
        .where(ChatHistory.pii_scrubbed.is_(False))
        .order_by(ChatHistory.id)
        .limit(batch_size)
    )
    return session.scalars(statement)


def _replace(match: re.Match[str], kind: str, registry: _PlaceholderRegistry) -> str:
    value = match.group(0)
    if value.startswith("<") and value.endswith(">"):
        return value
    return registry.placeholder_for(kind, value)
