"""Puertos LLM del runtime y su implementacion Gemini.

El orquestador depende de dos *puertos* (Protocols), no de Gemini:

- ``Conversador.draft_nl(compiled) -> str``: redacta la respuesta NL a partir
  del Contexto Compilado (persona/estrategia/grounding vienen de la KB).
- ``TraitMapper.extract_traits(...)``: mapea el texto del turno a trait_ids del
  catalogo (Perfilador).

``GeminiConversador`` y ``GeminiTraitMapper`` son las implementaciones reales
(Vertex ADC o API key via ``google-genai``). Los tests inyectan fakes que
cumplen el mismo Protocol, asi el cableado completo se prueba sin red.
"""
from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, Protocol

from kb_agent.perfilador.extractor import TraitCandidate

#: Identidad de emergencia si la KB no declara SelfDeclaration (no deberia pasar).
_IDENTITY_LAST_RESORT = (
    "Eres un asistente. Responde en español, breve y amable, usando "
    "EXCLUSIVAMENTE los datos provistos."
)


class Conversador(Protocol):
    def draft_nl(self, compiled: dict[str, Any]) -> str: ...


class TraitMapper(Protocol):
    def extract_traits(
        self,
        *,
        turn_text: str,
        candidates: Sequence[TraitCandidate],
        instructions: str,
    ) -> Sequence[Any]: ...


def build_nl_prompt(compiled: dict[str, Any]) -> str:
    """Prompt del Conversador. Todo lo del negocio sale del Contexto Compilado."""
    persona = compiled.get("persona", {}) or {}
    strategy = compiled.get("strategy", "")
    identity_lines: list[str] = []
    if persona.get("whoami"):
        identity_lines.append(persona["whoami"])
    if persona.get("estilo"):
        identity_lines.append(f"Estilo: {persona['estilo']}")
    if persona.get("limites"):
        identity_lines.append(f"Limites: {persona['limites']}")
    if strategy:
        identity_lines.append(f"Estrategia: {strategy}")
    identity = "\n".join(identity_lines) or _IDENTITY_LAST_RESORT

    facts = [f["body"] for f in compiled.get("domain_facts", [])]
    rules = [r["body"] for r in compiled.get("rules", [])]
    traits = compiled.get("user_traits", [])
    grounding = "\n".join(f"- {t}" for t in facts + rules)
    perfil = f"\nPERFIL DEL CLIENTE (traits): {', '.join(traits)}" if traits else ""
    system_turn = compiled.get("system_turn")
    system_turn_prompt = ""
    if isinstance(system_turn, dict) and system_turn.get("content"):
        system_turn_prompt = (
            "\n\nRESULTADO DE TOOL (System Turn JSON crudo):\n"
            f"{system_turn['content']}\n"
            "Usa este resultado para responder al cliente sin inventar datos fuera del JSON ni del grounding."
        )
    return (
        f"{identity}\n\n"
        "Responde usando EXCLUSIVAMENTE los datos de abajo. "
        "Si hay traits del cliente, adapta la sugerencia a su perfil. "
        "No inventes nada fuera de estos datos.\n\n"
        f"DATOS:\n{grounding}{perfil}{system_turn_prompt}\n\n"
        f"PREGUNTA: {compiled['question']}\n\nRESPUESTA:"
    )


def build_trait_prompt(turn_text: str, candidates: Sequence[TraitCandidate]) -> str:
    catalogo = "\n".join(f"- {c.id}: {c.body}" for c in candidates)
    return (
        "Analiza el mensaje del cliente y determina si revela EXPLICITAMENTE "
        "alguna de las caracteristicas del catalogo. Solo caracteristicas dichas "
        "explicitamente, no inferencias.\n\n"
        f"CATALOGO DE TRAITS:\n{catalogo}\n\n"
        f"MENSAJE: {turn_text}\n\n"
        "Responde SOLO un array JSON con los traits detectados, formato: "
        '[{"trait_id": "<id exacto del catalogo>", "confidence": <0..1>}]. '
        "Si no hay ninguno, responde []."
    )


def parse_trait_json(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[.*\]", text or "", flags=re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


class GeminiConversador:
    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self.model = model

    def draft_nl(self, compiled: dict[str, Any]) -> str:
        resp = self._client.models.generate_content(model=self.model, contents=build_nl_prompt(compiled))
        return (resp.text or "").strip()


class GeminiTraitMapper:
    """TraitMapper real: usa Gemini para mapear texto -> trait_ids."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self.model = model

    def extract_traits(
        self,
        *,
        turn_text: str,
        candidates: Sequence[TraitCandidate],
        instructions: str,
    ) -> list[dict[str, Any]]:
        resp = self._client.models.generate_content(
            model=self.model, contents=build_trait_prompt(turn_text, candidates)
        )
        return parse_trait_json(resp.text or "")


def make_gemini_client() -> Any:
    """Crea el cliente ``google-genai`` (Vertex ADC o API key segun entorno)."""
    from google import genai

    return genai.Client()
