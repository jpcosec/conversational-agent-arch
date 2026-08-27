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
from frontends.chat.demo_data import (
    build_reply_text,
    demo_context_items,
    extract_slots,
    infer_intent,
    next_flow_node,
)


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
        trait_ids = [t["trait_id"] if isinstance(t, dict) else str(t) for t in traits]
        suffix = f" (perfil: {', '.join(trait_ids)})" if trait_ids else ""
        return f"[nl] {' | '.join(facts[:2])}{suffix}"


class DemoStateMachineConversador:
    """LLM fake para el modo demo con máquina de estados determinista."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def handle_turn(self, session: dict[str, Any], user_message: str) -> dict[str, Any]:
        intent = infer_intent(user_message)
        session.setdefault("slots", {})
        session.setdefault("traits", [])
        session.setdefault("history", [])
        extracted = extract_slots(user_message)
        session["slots"].update(extracted)
        if session.get("flow_node") == "obtencion_datos" and extracted:
            intent = "recordatorio"

        if intent == "ansiedad" and "trait-antonia-ansioso-aplicacion" not in session["traits"]:
            session["traits"].append("trait-antonia-ansioso-aplicacion")
        if intent == "recordatorio" and "trait-antonia-prefiere-recordatorios" not in session["traits"]:
            session["traits"].append("trait-antonia-prefiere-recordatorios")
        if not session.get("history"):
            session["traits"].append("trait-antonia-primera-vez") if "trait-antonia-primera-vez" not in session["traits"] else None

        tool_ready = intent == "recordatorio" and session["slots"].get("dia") and session["slots"].get("hora")
        flow_node = next_flow_node(session.get("flow_node"), intent, session["slots"], tool_just_ran=tool_ready)
        kind = "tool_call" if tool_ready else "fallback" if intent == "fallback" else "nl"
        items = demo_context_items(intent, flow_node, session, user_message)
        reply_text = build_reply_text(intent, flow_node, session, user_message)

        state_trace = ["IDLE", "EVALUATING_CONTEXT"]
        if kind == "tool_call":
            state_trace += ["WAITING_TOOL", "DRAFTING_RESPONSE"]
        elif kind == "fallback":
            state_trace += ["BREAKPOINT_MISS", "DRAFTING_RESPONSE"]
        else:
            state_trace += ["DRAFTING_RESPONSE"]

        system_turn = None
        if kind == "tool_call":
            system_turn = {
                "tool": "agendar_recordatorio",
                "status": "ok",
                "args": {
                    "dia": session["slots"].get("dia"),
                    "hora": session["slots"].get("hora"),
                    "nombre": session.get("nombre") or "Paciente demo",
                },
                "content": f"Recordatorio semanal agendado para {session['slots'].get('dia')} a las {session['slots'].get('hora')}",
            }

        raw = {
            "question": user_message,
            "reply_text": reply_text,
            "kind": kind,
            "scenario_effective": "psp-selfix-demo",
            "scenario_source": "demo_mode",
            "state_trace": state_trace,
            "flow_node": flow_node,
            "allowed_transitions": [e["target"] for e in []],
            "traits_after": list(session["traits"]),
            "system_turn": system_turn,
            "context": {
                "scenario": "psp-selfix-demo",
                "atom_ids": [i["atom_id"] for i in items],
                "include_tags": sorted({tag for i in items for tag in i.get("tags", [])}),
                "items": items,
                "tools": [i for i in items if i.get("role") == "tool"],
                "user_traits": [
                    {"trait_id": trait_id, "confidence": 0.9, "source": "demo"}
                    for trait_id in session["traits"]
                ],
                "grounding_atoms": [i["atom_id"] for i in items if i.get("grounds_step")],
                "is_empty": kind == "fallback",
                "bundle": [
                    {"doc_id": i["atom_id"], "motivo": i.get("motivo"), "score": i.get("score")}
                    for i in items
                ],
            },
        }
        session["flow_node"] = "despedida" if kind == "tool_call" else flow_node
        session["history"].append({"role": "user", "content": user_message})
        session["history"].append({"role": "assistant", "content": reply_text})
        self.calls.append(raw)
        return raw


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


class FakeEmbedder:
    """Doble barato de ``fastembed.TextEmbedding`` para tests offline.

    El compilador (``ContextCompiler._semantic_candidates``, tarea 1.3) pide
    el embedder de ``knowledge_ops`` (``knowledge_ops._embedder()``) para
    embeder la pregunta de cada turno cuando hay ``knowledge_ops`` inyectado
    -- y ``Orchestrator.__init__`` SIEMPRE crea una instancia real de
    ``KnowledgeOperations``. Cargar el embedder real (jina-embeddings-v2)
    puede tomar bastante en frio (ver ``KnowledgeOperations._embedder``), y
    cada test que arma un ``Orchestrator`` via ``offline_orchestrator`` crea
    una instancia nueva. Sin este doble, la suite entera pagaria ese costo
    por cada test -- se lo inyecta directo en ``_embedder_cache`` (mismo
    mecanismo de cacheo por instancia que usa el codigo real, ver su
    docstring).

    Vector fijo (no todo-ceros, para que la similitud coseno no divida por
    cero) del mismo largo que ``jina-embeddings-v2-base-es`` (768).
    Determinista: no importa el ranking exacto en estos tests, ninguno
    afirma sobre el contenido del bundle/domain_facts vía similitud real.
    """

    _DIM = 768

    def embed(self, texts: Any) -> list[list[float]]:
        return [[0.01] * self._DIM for _ in texts]


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
    orch = Orchestrator(
        kb_root=kb_root,
        db_url=db_url,
        conversador=conversador or FakeConversador(),
        trait_mapper=trait_mapper or FakeTraitMapper(VEGETARIAN_MATCH),
        tool_handlers=tool_handlers,
        **kwargs,
    )
    orch.knowledge_ops._embedder_cache = FakeEmbedder()
    return orch
