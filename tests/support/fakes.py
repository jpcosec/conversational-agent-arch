"""Dobles de los puertos LLM (``kb_agent.llm.Conversador`` / ``TraitMapper``).

Permiten ejercer el cableado COMPLETO del orquestador (router, compilador,
policy, tools, SQL, perfilador) sin red. Son deterministas y registran las
llamadas para que los tests afirmen sobre lo que el runtime le pidio al LLM.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from kb_agent.agent import decide_turn
from kb_agent.agents.orchestrator_agent import apply_transition_guard
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
        trait_ids = [t["trait_id"] if isinstance(t, dict) else str(t) for t in traits]
        suffix = f" (perfil: {', '.join(trait_ids)})" if trait_ids else ""
        return f"[nl] {' | '.join(facts[:2])}{suffix}"


class FakeGate:
    """Veredicto determinista para tests offline (``GateAgent``, fase 2.3).

    ``Orchestrator.__init__`` construye un ``GateAgent`` real (que necesita
    un cliente LLM) cuando no se inyecta ``gate=...``. Este doble evita esa
    construccion -- y cualquier llamada a un modelo -- en
    ``offline_orchestrator``, igual que ``FakeConversador``/``FakeTraitMapper``
    evitan la llamada real para el resto del turno.

    Por defecto aprueba todo (``approved=True``). ``verdict_fn`` permite
    simular un rechazo del juez; ``raises=True`` hace que ``evaluate`` lance,
    para ejercer el fail-open de ``Orchestrator._policy_gate``.
    """

    def __init__(
        self,
        verdict_fn: Callable[..., dict[str, Any]] | None = None,
        *,
        raises: bool = False,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._verdict_fn = verdict_fn
        self._raises = raises

    def evaluate(
        self,
        response: str,
        *,
        tool_called: bool,
        tool_name: str | None = None,
        step: str | None = None,
        session_tools_called: Sequence[str] = (),
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "response": response,
                "tool_called": tool_called,
                "tool_name": tool_name,
                "step": step,
                "session_tools_called": list(session_tools_called),
            }
        )
        if self._raises:
            raise RuntimeError("FakeGate: fallo simulado del juez")
        if self._verdict_fn is not None:
            return self._verdict_fn(response, tool_called=tool_called, tool_name=tool_name, step=step)
        return {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}


class FakeOrchestratorAgent:
    """Decision determinista para tests offline (``OrchestratorAgent``, fase 2.4).

    ``Orchestrator.__init__`` construye un ``OrchestratorAgent`` real (que
    necesita un cliente LLM) cuando no se inyecta ``orchestrator_agent=...``.
    Este doble evita esa construccion -- y cualquier llamada a un modelo --
    en ``offline_orchestrator``, igual que ``FakeGate``/``FakeConversador``
    evitan la llamada real para el resto del turno.

    Por defecto DELEGA en ``kb_agent.agent.decide_turn`` (la policy pura sin
    LLM, previa a fase 2.4): asi el runtime offline sigue produciendo
    EXACTAMENTE las mismas decisiones que antes (tool_call por keywords,
    fallback si no hay grounding, nl en el resto) sin tocar los tests que ya
    ejercitan ese comportamiento -- ``decide_turn`` es, en los hechos, el
    fallback deterministico "sin LLM" que describe el plan de fase 2.4.

    Pasale ``decision_fn`` para forzar una decision arbitraria (p.ej. un
    ``kind: "tool_call"`` que ``decide_turn`` nunca elegiria por keywords, o
    un ``step_target`` fuera de ``allowed_transitions`` para ejercer el
    veto). En AMBOS casos (default y ``decision_fn``) se aplica la MISMA
    guardia de codigo que usa el ``OrchestratorAgent`` real
    (``apply_transition_guard``): el fake no es una via para saltarse la
    guardia, es otra fuente de decision sujeta a ella.
    """

    def __init__(self, decision_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._decision_fn = decision_fn

    def decide(self, compiled_context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(compiled_context)
        allowed_transitions = [str(t) for t in (compiled_context.get("allowed_transitions") or [])]

        raw: dict[str, Any] = (
            dict(self._decision_fn(compiled_context))
            if self._decision_fn is not None
            else dict(decide_turn(compiled_context))
        )
        raw.setdefault("reason", "decision determinista (fallback sin LLM: decide_turn)")

        step_target, vetoed = apply_transition_guard(raw.pop("flow_target", None), allowed_transitions)
        result: dict[str, Any] = {"kind": raw.get("kind", "nl"), "reason": raw["reason"]}
        if "function_call" in raw:
            result["function_call"] = raw["function_call"]
        if step_target:
            result["flow_target"] = step_target
        if vetoed:
            result["step_target_vetado"] = vetoed
        return result


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
    gate: FakeGate | None = None,
    orchestrator_agent: FakeOrchestratorAgent | None = None,
    tool_handlers: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Orchestrator:
    """Orquestador completo con LLM fake (sin credenciales, sin red)."""
    orch = Orchestrator(
        kb_root=kb_root,
        db_url=db_url,
        conversador=conversador or FakeConversador(),
        trait_mapper=trait_mapper or FakeTraitMapper(VEGETARIAN_MATCH),
        gate=gate or FakeGate(),
        orchestrator_agent=orchestrator_agent or FakeOrchestratorAgent(),
        tool_handlers=tool_handlers,
        **kwargs,
    )
    orch.knowledge_ops._embedder_cache = FakeEmbedder()
    return orch
