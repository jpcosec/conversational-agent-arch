from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from textwrap import dedent
from typing import Any

from google.adk.agents import LlmAgent

from .kb_tools import list_topics, read_atom, search_knowledge


CANONICAL_FALLBACK_RESPONSE = "No tengo esa información a mano, la averiguaré."
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
)
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


def build_conversador_system_instruction(
    _readonly_context: Any | None = None,
    *,
    compiled_context: Mapping[str, Any] | None = None,
) -> str:
    """Construye el system prompt del Conversador con guardrails estrictos.

    El prompt deja explícito que el agente solo puede responder usando
    ``domain_facts`` y ``rules`` del Contexto Compilado. Cuando el payload
    llega vacío, la frase canónica se resuelve fuera del modelo con
    ``draft_conversador_response``.
    """
    prompt = dedent(
        f"""
        Eres el conversador de una base de conocimiento APOS/APOE.

        Tu función es conversar con una persona experta y mediar el acceso a la base.
        Para recuperar conocimiento debes usar SIEMPRE al sub-agente bibliotecario.

        Reglas críticas:
        - Responde en español.
        - Está PROHIBIDO responder con conocimiento paramétrico, memoria general o inferencias externas al payload recibido.
        - SOLO puedes usar los `domain_facts` y `rules` del Contexto Compilado actual.
        - Si faltan datos en `domain_facts`/`rules`, dilo sin completar huecos ni inventar información.
        - Si `is_empty=true`, la respuesta final debe ser EXACTAMENTE: "{CANONICAL_FALLBACK_RESPONSE}"
        - Conserva los ids `atom-...` solo si vienen en `domain_facts`/`rules`.
        - Mantén la respuesta corta: máximo 180 palabras.

        Comportamiento:
        - Si la consulta es ambigua, primero aclárala brevemente.
        - No guardas notas todavía. En esta etapa solo retrieval.
        - Después de recuperar, explica en lenguaje natural y con buena estructura.

        Estilo:
        - conciso
        - directo
        - útil para una conversación con experto
        """
    ).strip()

    if compiled_context is None:
        return prompt

    return f"{prompt}\n\nContexto compilado actual:\n{render_compiled_context(compiled_context)}"


def render_compiled_context(compiled_context: Mapping[str, Any]) -> str:
    rules = _normalize_items(compiled_context.get("rules"))
    domain_facts = _normalize_items(compiled_context.get("domain_facts"))
    function_declarations = build_function_declarations(compiled_context)
    lines = [
        f"scenario: {compiled_context.get('scenario') or ''}",
        f"question: {compiled_context.get('question') or ''}",
        f"is_empty: {bool(compiled_context.get('is_empty'))}",
        "rules:",
        *[f"- {item['id']}: {item['body']}" for item in rules],
        "domain_facts:",
        *[f"- {item['id']}: {item['body']}" for item in domain_facts],
        "function_declarations:",
        *[
            f"- {declaration['name']}: required={declaration['parameters'].get('required', [])}"
            for declaration in function_declarations
        ],
    ]
    return "\n".join(lines)


def draft_conversador_response(compiled_context: Mapping[str, Any]) -> Any:
    """Devuelve la salida del Conversador para el payload compilado.

    - Si ``is_empty`` es ``True`` y no hay tool calling aplicable, corta por lo
      sano y devuelve la frase canónica.
    - Si hay tools relevantes y la intención las requiere, emite un
      ``function_call`` estructurado.
    - Si hay grounding disponible, construye una respuesta estrictamente basada
      en ``rules`` y ``domain_facts`` sin introducir contenido extra.
    """
    function_declarations = build_function_declarations(compiled_context)
    question = str(compiled_context.get("question") or "")
    selected_tool = _select_relevant_tool(question, function_declarations)
    if selected_tool is not None:
        args = _extract_function_args(question, selected_tool["parameters"])
        missing_required_args = _missing_required_args(args, selected_tool["parameters"])
        if missing_required_args:
            return _build_missing_args_question(missing_required_args, selected_tool["parameters"])
        if _args_match_schema(args, selected_tool["parameters"]):
            return {"function_call": {"name": selected_tool["name"], "args": args}}

    if bool(compiled_context.get("is_empty")):
        return CANONICAL_FALLBACK_RESPONSE

    rules = _normalize_items(compiled_context.get("rules"))
    domain_facts = _normalize_items(compiled_context.get("domain_facts"))
    grounded_lines: list[str] = []
    if rules:
        grounded_lines.extend(item["body"] for item in rules)
    if domain_facts:
        grounded_lines.extend(item["body"] for item in domain_facts)

    if not grounded_lines:
        return CANONICAL_FALLBACK_RESPONSE

    return "\n".join(grounded_lines)


def build_function_declarations(compiled_context: Mapping[str, Any] | None) -> list[dict[str, Any]]:
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

    parameters = dict(schema_source)
    parameters.pop("name", None)
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
        if any(token in candidate_tokens for token in ("calendar", "calendario", "agenda", "cita", "book", "booking")):
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


def _extract_arg_value(question: str, arg_name: str, arg_schema: Mapping[str, Any]) -> Any | None:
    normalized_name = _normalize_text(arg_name)
    enum_values = arg_schema.get("enum")
    if isinstance(enum_values, Sequence) and not isinstance(enum_values, (str, bytes)):
        for enum_value in enum_values:
            text = str(enum_value)
            if _normalize_text(text) in _normalize_text(question):
                return text

    if normalized_name in {"date", "fecha", "day"}:
        for pattern in _DATE_VALUE_PATTERNS:
            match = re.search(pattern, question, flags=re.IGNORECASE)
            if match:
                return match.group(0)

    if normalized_name in {"hora", "time"}:
        match = re.search(_TIME_VALUE_PATTERN, question)
        if match:
            return match.group(0)

    if arg_schema.get("type") == "integer":
        match = re.search(_INTEGER_VALUE_PATTERN, question)
        if match:
            return int(match.group(0))

    if normalized_name in {"nombre", "name"}:
        extracted_name = _extract_name_value(question)
        if extracted_name:
            return extracted_name

    if normalized_name in {"service", "servicio"}:
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


def _build_missing_args_question(missing_args: Sequence[str], schema: Mapping[str, Any]) -> str:
    properties = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
    prompts = [_arg_prompt(arg_name, properties.get(arg_name, {})) for arg_name in missing_args]
    if len(prompts) == 1:
        return prompts[0]
    return "Necesito estos datos para continuar: " + "; ".join(prompts)


def _arg_prompt(arg_name: str, arg_schema: Any) -> str:
    normalized_name = _normalize_text(arg_name)
    if normalized_name in {"date", "fecha", "day"}:
        return "¿Qué fecha necesitas?"
    if normalized_name in {"service", "servicio"}:
        return "¿Qué servicio necesitas reservar?"
    if isinstance(arg_schema, Mapping):
        title = arg_schema.get("title") or arg_schema.get("description")
        if title:
            return f"Necesito este dato: {title}."
    return f"Necesito el dato '{arg_name}' para continuar."


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


bibliotecario = LlmAgent(
    name="bibliotecario",
    model="gemini-2.5-flash",
    instruction="""
        Eres el bibliotecario de una base de conocimiento APOS construida sobre SLDB.

        Tu trabajo es SOLO retrieval.

        Herramientas:
        - list_topics: lista los tags/topics disponibles.
        - search_knowledge: busca átomos por tag semántico o por nombre literal.
        - read_atom: abre un átomo específico y devuelve su contenido estructurado.

        Reglas:
        1. Primero orienta la búsqueda: si el usuario pide un concepto, intenta buscar por tag semántico.
        2. Si no sabes qué tag usar, llama list_topics antes de buscar.
        3. Nunca inventes contenido que no venga de los átomos recuperados.
        4. Abre solo los 2-4 átomos más relevantes.
        5. Responde breve: máximo 6 bullets y máximo 220 palabras.
        6. Siempre menciona explícitamente los ids `atom-...` usados.
        7. Si la búsqueda no devuelve nada, dilo en una línea y sugiere un tag cercano.

        Tu rol NO es corregir, escribir ni guardar nada. Solo recuperar y explicar.
    """,
    tools=[list_topics, search_knowledge, read_atom],
)


root_agent = LlmAgent(
    name="conversador_apos",
    model="gemini-2.5-flash",
    instruction=build_conversador_system_instruction,
    sub_agents=[bibliotecario],
)
