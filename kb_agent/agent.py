"""Policy PURA de turno del Conversador.

Este modulo NO llama a ningun LLM ni conoce el negocio. Solo decide, de forma
deterministica y testeable, que clase de turno corresponde a partir del
Contexto Compilado (``CompiledDocument.to_dict()``):

- ``{"kind": "tool_call", "function_call": {...}}`` cuando hay tool relevante
  y los argumentos requeridos pudieron extraerse del mensaje;
- ``{"kind": "fallback"}`` cuando el contexto viene vacio o sin grounding;
- ``{"kind": "nl"}`` en cualquier otro caso (redacta el Conversador con LLM).

El texto del fallback vive en la KB (``FallbackRule``); ``DEFAULT_FALLBACK_MESSAGE``
es solo el ultimo recurso si la KB no declara uno y el proyecto tampoco.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

#: Ultimo recurso si ni la KB (FallbackRule) ni project.config.yaml definen fallback.
DEFAULT_FALLBACK_MESSAGE = "No tengo esa información a mano, la averiguaré."

# ── heuristicas lexicas de intencion de tool (es) ─────────────────────────────
# Son deliberadamente simples: la policy debe ser barata y sin LLM. Cubren el
# vocabulario de "agendar/reservar" en espanol; una KB con tools de otra
# naturaleza deberia extender estas listas (o reemplazar la policy).
_TOOL_INTENT_KEYWORDS = (
    "agenda",
    "agendar",
    "agendame",
    "agéndame",
    "cita",
    "reserv",
    "turno",
    "calendar",
    "calendario",
    "disponibilidad",
    "recordatorio",
)
_TOOL_AFFINITY_TOKENS = ("calendar", "calendario", "agenda", "cita", "book", "booking", "reserva", "recordatorio")
_DATE_ARG_NAMES = {"date", "fecha", "day", "dia"}
_TIME_ARG_NAMES = {"hora", "time"}
_NAME_ARG_NAMES = {"nombre", "name"}
_SERVICE_ARG_NAMES = {"service", "servicio"}
_DATE_VALUE_PATTERNS = (
    r"pasado\s+mañana",
    r"pasado\s+manana",
    r"mañana",
    r"manana",
    r"hoy",
    r"lunes",
    r"martes",
    r"miércoles",
    r"miercoles",
    r"jueves",
    r"viernes",
    r"sábado",
    r"sabado",
    r"domingo",
    r"\d{1,2}/\d{1,2}(?:/\d{2,4})?",
    r"\d{4}-\d{2}-\d{2}",
)
_TIME_VALUE_PATTERN = r"\b\d{1,2}:\d{2}\b"
_INTEGER_VALUE_PATTERN = r"\b\d+\b"
_NAME_CAPTURE_STOP_WORDS = (
    " el ",
    " la ",
    " los ",
    " las ",
    " a las ",
    " al ",
    " de ",
    " del ",
    " para ",
)


def decide_turn(compiled_context: Mapping[str, Any]) -> dict[str, Any]:
    """Decide el tipo de turno sin redactar ni llamar al LLM."""
    function_declarations = build_function_declarations(compiled_context)
    question = str(compiled_context.get("question") or "")
    selected_tool = _select_relevant_tool(question, function_declarations)
    if selected_tool is not None:
        args = _extract_function_args(question, selected_tool["parameters"])
        if not _missing_required_args(args, selected_tool["parameters"]) and _args_match_schema(
            args, selected_tool["parameters"]
        ):
            return {"kind": "tool_call", "function_call": {"name": selected_tool["name"], "args": args}}

    if bool(compiled_context.get("is_empty")):
        return {"kind": "fallback"}

    rules = _normalize_items(compiled_context.get("rules"))
    domain_facts = _normalize_items(compiled_context.get("domain_facts"))
    if not rules and not domain_facts:
        return {"kind": "fallback"}

    return {"kind": "nl"}


def build_function_declarations(compiled_context: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Normaliza los ToolAtom del contexto a function_declarations planas."""
    if compiled_context is None:
        return []

    raw_tools = compiled_context.get("tools")
    if not isinstance(raw_tools, Sequence) or isinstance(raw_tools, (str, bytes)):
        return []

    declarations: list[dict[str, Any]] = []
    for raw_tool in raw_tools:
        declaration = _normalize_function_declaration(raw_tool)
        if declaration is not None:
            declarations.append(declaration)
    return declarations


def _normalize_function_declaration(raw_tool: Any) -> dict[str, Any] | None:
    if not isinstance(raw_tool, Mapping):
        return None

    schema_source = raw_tool.get("json_schema") if isinstance(raw_tool.get("json_schema"), Mapping) else raw_tool
    if not isinstance(schema_source, Mapping):
        return None

    tool_id = raw_tool.get("id") or schema_source.get("name") or schema_source.get("$id") or schema_source.get("id")
    if not tool_id:
        return None

    # El ToolAtom del KB puede venir en dos formas:
    #  (a) plano: {name, properties, required, type}
    #  (b) anidado: {name, parameters: {type, properties, required}}
    # Normalizamos ambas a un unico nivel de parameters con properties.
    inner = schema_source.get("parameters")
    if isinstance(inner, Mapping) and "properties" in inner:
        parameters = dict(inner)
    else:
        parameters = dict(schema_source)
        parameters.pop("name", None)
        parameters.pop("parameters", None)
    return {
        "name": str(tool_id),
        "description": str(raw_tool.get("body") or schema_source.get("description") or ""),
        "parameters": parameters,
    }


def _normalize_items(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return []

    normalized: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        normalized.append(
            {
                "id": str(item.get("id") or ""),
                "body": str(item.get("body") or ""),
            }
        )
    return normalized


def _select_relevant_tool(question: str, function_declarations: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not question or not function_declarations or not _question_requires_tool(question):
        return None

    question_tokens = set(_tokenize(question))
    ranked: list[tuple[int, dict[str, Any]]] = []
    for declaration in function_declarations:
        candidate = dict(declaration)
        candidate_tokens = set(_tokenize(" ".join([
            str(candidate.get("name") or ""),
            str(candidate.get("description") or ""),
            " ".join(str(name) for name in candidate.get("parameters", {}).get("properties", {}).keys()),
        ])))
        score = len(question_tokens & candidate_tokens)
        if any(token in candidate_tokens for token in _TOOL_AFFINITY_TOKENS):
            score += 2
        ranked.append((score, candidate))

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_candidate = ranked[0]
    if best_score <= 0 and len(ranked) != 1:
        return None
    return best_candidate


def _question_requires_tool(question: str) -> bool:
    normalized = _normalize_text(question)
    return any(keyword in normalized for keyword in _TOOL_INTENT_KEYWORDS)


def _extract_function_args(question: str, schema: Mapping[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return {}

    extracted: dict[str, Any] = {}
    for arg_name, arg_schema in properties.items():
        if not isinstance(arg_schema, Mapping):
            continue
        value = _extract_arg_value(question, arg_name, arg_schema)
        if value is not None:
            extracted[str(arg_name)] = value
    return extracted


def _mask_date_and_time_spans(question: str) -> str:
    """Blank out date/time substrings so integer extraction ignores their digits.

    E.g. ``"2026-09-10"`` (an ISO date) or ``"20:00"`` (a time) contain digits
    that must not be mistaken for a standalone integer argument (like a
    party size). Matches are replaced with ``#`` of the same length so span
    positions and non-digit context (spaces, punctuation) are preserved.
    """

    masked = question
    for pattern in (*_DATE_VALUE_PATTERNS, _TIME_VALUE_PATTERN):
        masked = re.sub(pattern, lambda m: "#" * len(m.group(0)), masked, flags=re.IGNORECASE)
    return masked


def _extract_arg_value(question: str, arg_name: str, arg_schema: Mapping[str, Any]) -> Any | None:
    normalized_name = _normalize_text(arg_name)
    enum_values = arg_schema.get("enum")
    if isinstance(enum_values, Sequence) and not isinstance(enum_values, (str, bytes)):
        for enum_value in enum_values:
            text = str(enum_value)
            if _normalize_text(text) in _normalize_text(question):
                return text

    if normalized_name in _DATE_ARG_NAMES:
        for pattern in _DATE_VALUE_PATTERNS:
            match = re.search(pattern, question, flags=re.IGNORECASE)
            if match:
                return match.group(0)

    if normalized_name in _TIME_ARG_NAMES:
        match = re.search(_TIME_VALUE_PATTERN, question)
        if match:
            return match.group(0)

    if arg_schema.get("type") == "integer":
        masked_question = _mask_date_and_time_spans(question)
        match = re.search(_INTEGER_VALUE_PATTERN, masked_question)
        if match:
            return int(match.group(0))

    if normalized_name in _NAME_ARG_NAMES:
        extracted_name = _extract_name_value(question)
        if extracted_name:
            return extracted_name

    if normalized_name in _SERVICE_ARG_NAMES:
        lowered_question = _normalize_text(question)
        for marker in ("para ", "de "):
            if marker in lowered_question:
                service = lowered_question.split(marker, 1)[1].strip(" .,!?")
                if service:
                    return service

    return None


def _extract_name_value(question: str) -> str | None:
    for pattern in (
        r"a\s+nombre\s+de\s+(.+)$",
        r"nombre\s+(?:de\s+)?(.+)$",
        r"para\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ' -]*)$",
    ):
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_name_candidate(match.group(1))
        if candidate:
            return candidate
    return None


def _clean_name_candidate(candidate: str) -> str:
    cleaned = candidate.strip(" .,!?;:")
    lowered = cleaned.casefold()
    cut_positions = [lowered.find(stop_word) for stop_word in _NAME_CAPTURE_STOP_WORDS if lowered.find(stop_word) > 0]
    if cut_positions:
        cleaned = cleaned[: min(cut_positions)].strip(" .,!?;:")
    return cleaned


def _missing_required_args(args: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    required = schema.get("required")
    if not isinstance(required, Sequence) or isinstance(required, (str, bytes)):
        return []
    return [str(name) for name in required if not _has_non_empty_value(args.get(str(name)))]


def _args_match_schema(args: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    if _missing_required_args(args, schema):
        return False

    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return True

    for arg_name, arg_value in args.items():
        property_schema = properties.get(arg_name)
        if not isinstance(property_schema, Mapping):
            continue
        expected_type = property_schema.get("type")
        if expected_type == "string" and not isinstance(arg_value, str):
            return False
        if expected_type == "integer" and not isinstance(arg_value, int):
            return False
        if expected_type == "number" and not isinstance(arg_value, (int, float)):
            return False
        if expected_type == "boolean" and not isinstance(arg_value, bool):
            return False
        if expected_type == "array" and not isinstance(arg_value, list):
            return False
        if expected_type == "object" and not isinstance(arg_value, Mapping):
            return False
    return True


def _has_non_empty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [token for token in re.split(r"[^a-z0-9]+", normalized) if token]


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()
