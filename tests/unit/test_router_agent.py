"""Tests de ``kb_agent.agents.router.RouterAgent`` (fase 2.2), todos sin red.

Cubre: el render del prompt fijo (familias, motivos, regla de oro), el
contrato ``route`` con un modelo fake (incluido el loop de tools -- el
modelo pide ``explore_multi``/``explore``/``show`` sobre un doble de
``KnowledgeOperations`` antes de responder), y ``apply_security_floor`` -- la
guardia de codigo que fuerza el piso de seguridad sin importar que decida
el modelo (equivalente, para el ruteador, a ``apply_transition_guard`` del
orquestador).

El piso de seguridad END-TO-END contra la KB real (``ContextCompiler`` +
``FakeRouterAgent``, con las 6 ``RuleAtom conversation:security`` reales) se
prueba en ``tests/integration/test_router_security_floor.py``.
"""
from __future__ import annotations

from typing import Any

from kb_agent.agents.router import (
    RouterAgent,
    RouterDecision,
    apply_security_floor,
    render_router_instruction,
)


class _Resp:
    """Respuesta cruda minima, con la forma que expone google-genai."""

    def __init__(self, text: str = "", parsed: Any = None, function_calls: list[Any] | None = None) -> None:
        self.text = text
        self.parsed = parsed
        self.function_calls: list[Any] = function_calls or []


class _FakeModels:
    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return self._responder(kwargs)


class _FakeClient:
    def __init__(self, responder) -> None:
        self.models = _FakeModels(responder)

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self.models.calls


class _FakeKnowledgeOps:
    """Doble minimo de ``KnowledgeOperations``: solo lo que el ruteador usa."""

    def __init__(self) -> None:
        self.explore_multi_calls: list[dict[str, Any]] = []
        self.explore_calls: list[dict[str, Any]] = []
        self.show_calls: list[str] = []

    def explore_multi(self, query: str, max_results: int = 10) -> dict[str, Any]:
        self.explore_multi_calls.append({"query": query, "max_results": max_results})
        return {
            "query": query,
            "results": [{"id": "trait-antonia-ansioso-aplicacion", "score": 0.3955, "model": "TraitAtom"}],
            "top_score": 0.3955,
            "results_count": 1,
            "is_empty": False,
        }

    def explore(self, tag: str | None = None, atom: str | None = None) -> dict[str, Any]:
        self.explore_calls.append({"tag": tag, "atom": atom})
        return {"mode": "tag" if tag else "atom", "tag": tag, "atom": atom, "docs": ["trait-antonia-ansioso-aplicacion"]}

    def show(self, atom_id: str) -> dict[str, Any] | None:
        self.show_calls.append(atom_id)
        if atom_id == "no-existe":
            return None
        return {"id": atom_id, "title": "Ansiedad en la aplicacion", "description": "..."}


# ── render_router_instruction: prompt fijo, explicito ────────────────────
def test_render_router_instruction_documents_families_motivos_and_golden_rule() -> None:
    instruction = render_router_instruction()

    for family in ("self", "domain", "conversation", "user", "gate"):
        assert f"- {family}" in instruction or f"family `{family}`" in instruction or family in instruction

    # "grounding de <step_actual>": el placeholder es el NOMBRE DEL STEP, no el
    # id del documento. Con la redaccion anterior ("grounding de steps.<x>") el
    # modelo sustituia el doc_id y producia motivos como
    # "grounding de steps.atom-antonia-bienvenida", que es el texto que ve el
    # usuario en el Turn Inspector.
    for motivo in ("grounding de <step_actual>", "trait del usuario", "similitud <score>"):
        assert motivo in instruction

    assert "piso de seguridad" in instruction
    assert "conversation:security" in instruction
    # regla de oro: todo documento entra justificado
    assert "justifique" in instruction.lower() or "motivo" in instruction.lower()
    # las tools quedan documentadas, no son un misterio para el modelo
    assert "explore_multi" in instruction and "explore(" in instruction and "show(" in instruction


def test_router_agent_static_instruction_is_the_rendered_prompt() -> None:
    client = _FakeClient(lambda _kw: (_ for _ in ()).throw(AssertionError("no deberia llamarse")))
    agent = RouterAgent(client=client, model="gemini-test", knowledge_ops=_FakeKnowledgeOps())
    assert agent.static_instruction == render_router_instruction()


# ── route(): contrato con el modelo fake, incluido el loop de tools ──────
def test_route_declares_the_three_kb_tools_to_the_model() -> None:
    decision = RouterDecision(bundle=[])
    client = _FakeClient(lambda _kw: _Resp(text=decision.model_dump_json(), parsed=decision))
    agent = RouterAgent(client=client, model="gemini-test", knowledge_ops=_FakeKnowledgeOps())

    agent.route(question="me da miedo la aguja", active_step="conversation:steps.aplicacion")

    assert len(client.calls) == 1
    tool_names = {
        decl["name"]
        for block in client.calls[0]["config"]["tools"]
        for decl in block["function_declarations"]
    }
    assert tool_names == {"explore_multi", "explore", "show"}


def test_route_sends_question_step_and_traits_in_dynamic_context() -> None:
    decision = RouterDecision(bundle=[])
    client = _FakeClient(lambda _kw: _Resp(text=decision.model_dump_json(), parsed=decision))
    agent = RouterAgent(client=client, model="gemini-test", knowledge_ops=_FakeKnowledgeOps())

    agent.route(
        question="me da miedo la aguja, es la primera vez que me inyecto",
        active_step="conversation:steps.aplicacion",
        grounding_atoms=["atom-antonia-tecnica-aplicacion"],
        user_traits=[{"trait_id": "trait-antonia-ansioso-aplicacion", "confidence": 0.8}],
    )

    sent = client.calls[0]["contents"]
    blob = str(sent)
    assert "me da miedo la aguja" in blob
    assert "conversation:steps.aplicacion" in blob
    assert "atom-antonia-tecnica-aplicacion" in blob
    assert "trait-antonia-ansioso-aplicacion" in blob


def test_route_translates_history_role_content_into_role_text_turns() -> None:
    decision = RouterDecision(bundle=[])
    client = _FakeClient(lambda _kw: _Resp(text=decision.model_dump_json(), parsed=decision))
    agent = RouterAgent(client=client, model="gemini-test", knowledge_ops=_FakeKnowledgeOps())

    agent.route(
        question="y ahora que hago",
        active_step=None,
        history=[{"role": "user", "content": "hola"}, {"role": "assistant", "content": "hola, como estas"}],
    )

    contents = client.calls[0]["contents"]
    # 2 turnos de historial + el turno actual (dynamic_context)
    assert len(contents) == 3
    assert contents[0] == {"role": "user", "parts": [{"text": "hola"}]}
    assert contents[1] == {"role": "assistant", "parts": [{"text": "hola, como estas"}]}


def test_route_executes_tool_calls_against_knowledge_ops_before_final_answer() -> None:
    """El modelo pide explore_multi -> show antes de responder; ``route`` ejecuta
    esas tools contra el ``knowledge_ops`` inyectado (no uno nuevo) y le
    devuelve el resultado real al modelo antes de la respuesta final."""
    knowledge_ops = _FakeKnowledgeOps()
    final = RouterDecision(bundle=[
        {"doc_id": "trait-antonia-ansioso-aplicacion", "motivo": "el usuario expresa miedo a la aguja", "family": "user", "score": 0.3955},
    ])

    calls_seen: list[dict[str, Any]] = []

    def responder(kwargs: dict[str, Any]) -> _Resp:
        calls_seen.append(kwargs)
        if len(calls_seen) == 1:
            return _Resp(function_calls=[{"name": "explore_multi", "args": {"query": "miedo a la aguja"}}])
        if len(calls_seen) == 2:
            return _Resp(function_calls=[{"name": "show", "args": {"atom_id": "trait-antonia-ansioso-aplicacion"}}])
        return _Resp(text=final.model_dump_json(), parsed=final)

    client = _FakeClient(responder)
    agent = RouterAgent(client=client, model="gemini-test", knowledge_ops=knowledge_ops)

    bundle = agent.route(question="me da miedo la aguja", active_step=None)

    assert knowledge_ops.explore_multi_calls == [{"query": "miedo a la aguja", "max_results": 10}]
    assert knowledge_ops.show_calls == ["trait-antonia-ansioso-aplicacion"]
    assert bundle == [
        {"doc_id": "trait-antonia-ansioso-aplicacion", "motivo": "el usuario expresa miedo a la aguja", "family": "user", "score": 0.3955},
    ]


def test_route_show_tool_reports_missing_atom_instead_of_crashing() -> None:
    knowledge_ops = _FakeKnowledgeOps()
    final = RouterDecision(bundle=[])
    calls_seen: list[dict[str, Any]] = []

    def responder(kwargs: dict[str, Any]) -> _Resp:
        calls_seen.append(kwargs)
        if len(calls_seen) == 1:
            return _Resp(function_calls=[{"name": "show", "args": {"atom_id": "no-existe"}}])
        return _Resp(text=final.model_dump_json(), parsed=final)

    client = _FakeClient(responder)
    agent = RouterAgent(client=client, model="gemini-test", knowledge_ops=knowledge_ops)

    # No debe lanzar: la tool devuelve un error legible, no revienta el turno.
    assert agent.route(question="algo raro", active_step=None) == []


# ── apply_security_floor: la guardia de codigo, sin importar el modelo ───
def test_apply_security_floor_adds_missing_mandatory_ids() -> None:
    bundle = [{"doc_id": "domain-x", "motivo": "similitud 0.40", "family": "domain", "score": 0.40}]

    result = apply_security_floor(bundle, {"rule-security-a", "rule-security-b"})

    by_id = {e["doc_id"]: e for e in result}
    assert by_id["rule-security-a"]["motivo"] == "piso de seguridad"
    assert by_id["rule-security-b"]["motivo"] == "piso de seguridad"
    assert by_id["domain-x"]["motivo"] == "similitud 0.40"  # intacto


def test_apply_security_floor_empty_agent_bundle_still_yields_all_security_ids() -> None:
    """El caso del plan: el agente (fake) devuelve un bundle VACIO -- el piso
    de seguridad entra igual, completo."""
    security_ids = {f"rule-security-{i}" for i in range(6)}

    result = apply_security_floor([], security_ids)

    assert {e["doc_id"] for e in result} == security_ids
    assert all(e["motivo"] == "piso de seguridad" for e in result)


def test_apply_security_floor_prefixes_existing_motivo_without_losing_it() -> None:
    """Si el agente YA incluyo una regla de seguridad con otro motivo propio,
    la funcion antepone "piso de seguridad" sin descartar el motivo del
    agente -- se audita la razon completa."""
    bundle = [{"doc_id": "rule-security-a", "motivo": "similitud 0.31", "family": "domain", "score": 0.31}]

    result = apply_security_floor(bundle, {"rule-security-a"})

    assert result == [{"doc_id": "rule-security-a", "motivo": "piso de seguridad; similitud 0.31", "family": "domain", "score": 0.31}]


def test_apply_security_floor_does_not_duplicate_an_already_flagged_entry() -> None:
    bundle = [{"doc_id": "rule-security-a", "motivo": "piso de seguridad", "family": "domain", "score": None}]

    result = apply_security_floor(bundle, {"rule-security-a"})

    assert result == [{"doc_id": "rule-security-a", "motivo": "piso de seguridad", "family": "domain", "score": None}]


def test_apply_security_floor_preserves_agent_order_and_appends_missing_ids_sorted() -> None:
    bundle = [{"doc_id": "domain-b", "motivo": "similitud 0.5"}, {"doc_id": "domain-a", "motivo": "similitud 0.3"}]

    result = apply_security_floor(bundle, {"rule-z", "rule-a"})

    assert [e["doc_id"] for e in result] == ["domain-b", "domain-a", "rule-a", "rule-z"]
