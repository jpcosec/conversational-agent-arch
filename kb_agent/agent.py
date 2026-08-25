from __future__ import annotations

from collections.abc import Mapping, Sequence
from textwrap import dedent
from typing import Any

from google.adk.agents import LlmAgent

from .kb_tools import list_topics, read_atom, search_knowledge


CANONICAL_FALLBACK_RESPONSE = "No tengo esa información a mano, la averiguaré."


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
    lines = [
        f"scenario: {compiled_context.get('scenario') or ''}",
        f"question: {compiled_context.get('question') or ''}",
        f"is_empty: {bool(compiled_context.get('is_empty'))}",
        "rules:",
        *[f"- {item['id']}: {item['body']}" for item in rules],
        "domain_facts:",
        *[f"- {item['id']}: {item['body']}" for item in domain_facts],
    ]
    return "\n".join(lines)


def draft_conversador_response(compiled_context: Mapping[str, Any]) -> str:
    """Devuelve la salida del Conversador para el payload compilado.

    - Si ``is_empty`` es ``True``, corta por lo sano y devuelve la frase canónica.
    - Si hay grounding disponible, construye una respuesta estrictamente basada
      en ``rules`` y ``domain_facts`` sin introducir contenido extra.
    """
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
