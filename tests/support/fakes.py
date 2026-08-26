"""Dobles de los puertos LLM (``kb_agent.llm.Conversador`` / ``TraitMapper``).

Permiten ejercer el cableado COMPLETO del orquestador (router, compilador,
policy, tools, SQL, perfilador) sin red. Son deterministas y registran las
llamadas para que los tests afirmen sobre lo que el runtime le pidio al LLM.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from kb_agent.orchestrator import Orchestrator
from kb_agent.perfilador.extractor import TraitCandidate


class FakeConversador:
    """Redacta una respuesta determinista y grounded a partir del contexto compilado."""

    def __init__(self, responder: Callable[[dict[str, Any]], str] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responder = responder

    def draft_nl(self, compiled: dict[str, Any]) -> str:
        self.calls.append(compiled)
        if self._responder is not None:
            return self._responder(compiled)
        system_turn = compiled.get("system_turn")
        if isinstance(system_turn, dict) and system_turn.get("content"):
            return f"[tool-ok] {system_turn['content']}"
        facts = [f["body"] for f in compiled.get("domain_facts", [])]
        traits = compiled.get("user_traits", [])
        suffix = f" (perfil: {', '.join(traits)})" if traits else ""
        return f"[nl] {' | '.join(facts[:2])}{suffix}"


class FakeTraitMapper:
    """Mapea texto -> traits por palabras clave (``{"vegetarian": [{"trait_id": ..., "confidence": ...}]}``)."""

    def __init__(self, keyword_matches: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.keyword_matches = keyword_matches or {}
        self.calls: list[dict[str, Any]] = []

    def extract_traits(
        self,
        *,
        turn_text: str,
        candidates: Sequence[TraitCandidate],
        instructions: str,
    ) -> list[dict[str, Any]]:
        self.calls.append({"turn_text": turn_text, "candidates": list(candidates), "instructions": instructions})
        lowered = turn_text.lower()
        matches: list[dict[str, Any]] = []
        for keyword, found in self.keyword_matches.items():
            if keyword in lowered:
                matches.extend(found)
        return matches


class RecordingToolHandler:
    """Handler de tool que registra las llamadas (para KBs sin persistencia SQL propia)."""

    def __init__(self, name: str = "tool") -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def __call__(self, session: Any, user_id: int | None, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"user_id": user_id, "args": dict(args)})
        return {f"{self.name}_id": len(self.calls)}


VEGETARIAN_MATCH = {"vegetarian": [{"trait_id": "trait-vegetariano", "confidence": 0.9}]}


def offline_orchestrator(
    kb_root: Path,
    db_url: str = "sqlite:///:memory:",
    *,
    conversador: FakeConversador | None = None,
    trait_mapper: FakeTraitMapper | None = None,
    tool_handlers: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Orchestrator:
    """Orquestador completo con LLM fake (sin credenciales, sin red)."""
    return Orchestrator(
        kb_root=kb_root,
        db_url=db_url,
        conversador=conversador or FakeConversador(),
        trait_mapper=trait_mapper or FakeTraitMapper(VEGETARIAN_MATCH),
        tool_handlers=tool_handlers,
        **kwargs,
    )
