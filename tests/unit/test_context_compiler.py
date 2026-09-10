"""Knowledge: SLDB (modelos tipados) + SQL (traits) + grafo tipado de kgdb (flujo) -> CompiledDocument."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.knowledge.compiler import ContextCompiler, compile_context
from knowledge_base.operations import KnowledgeOperations
from tests.support.sldb_seed import minimal_business_atoms, seed_store


@dataclass
class SessionStateStub:
    active_domain: str | None = None
    flow_node: str | None = None


@pytest.fixture(scope="module")
def business_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    atoms = minimal_business_atoms() + [
        {
            "type": "boundary", "id": "boundary-negocio", "title": "Limites",
            "tags": ["self:limites", "system:negocio"],
            "fields": {"restriction": "No proceso pagos.", "conditions": "Siempre.", "escalation": "Derivar al local."},
        },
        {
            "type": "strategy", "id": "strategy-negocio", "title": "Estrategia",
            "tags": ["conversation:strategy", "system:negocio"],
            "fields": {"goal": "Resolver la consulta.", "approach": "Datos concretos.", "priorities": "Exactitud primero, luego cercania."},
        },
    ]
    return seed_store(tmp_path_factory.mktemp("kb") / "negocio", atoms)


@pytest.fixture()
def identity_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        user = Users(external_id="wa:+56999999999", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add_all([
            UserTraits(user_id=user.id, trait_id="trait-vegetariano", confidence=0.9, source="test"),
            UserTraits(user_id=user.id, trait_id="trait-prefiere-borde-relleno", confidence=0.7, source="test"),
        ])
        session.commit()
        yield session
    finally:
        session.close()


def test_compile_selects_by_typed_model_and_structures_by_semantic_role(business_root: Path, identity_session: Session) -> None:
    user_id = identity_session.query(Users.id).scalar()
    d = compile_context(
        question="¿Qué opciones vegetarianas tienen y hasta qué hora atienden?",
        user_id=user_id,
        knowledge=KnowledgeOperations(kb_root=business_root),
        identity_session=identity_session,
        session_state=SessionStateStub(),
    ).to_dict()

    assert [(f["id"], f["body"]) for f in d["domain_facts"]] == [
        ("domain-horarios", "Atendemos de 12:00 a 23:00."),
        ("domain-menu", "Pizza margarita 8900. Pizza cuatro quesos 9900."),
    ]
    assert [(r["id"], r["body"]) for r in d["rules"]] == [("rule-reservas", "Las reservas requieren confirmación previa.")]
    assert all({"tags", "title"} <= set(item) for item in d["domain_facts"] + d["rules"])
    # persona desde SelfDeclaration / StyleGuide / CapabilityBoundary
    assert d["persona"]["whoami"] == "Soy el asistente de la pizzeria."
    assert "Responde breve y amable." in d["persona"]["estilo"] and "Español chileno" in d["persona"]["estilo"]
    assert "No proceso pagos." in d["persona"]["limites"] and "Derivar al local." in d["persona"]["limites"]
    assert "Resolver la consulta." in d["strategy"] and "Exactitud primero" in d["strategy"]
    assert d["fallback_text"] == "Si no hay contexto suficiente, pide una aclaración."
    assert d["tools"] == [{"name": "crear_reserva", "parameters": {"type": "object", "properties": {"fecha": {"type": "string"}}, "required": ["fecha"]}}]
    # user_traits ahora son dicts resueltos contra su TraitAtom (trait_id +
    # title/description/category), no solo el id (esta KB no declara
    # TraitAtom para estos ids: title/description caen al fallback del id).
    assert [t["trait_id"] for t in d["user_traits"]] == ["trait-prefiere-borde-relleno", "trait-vegetariano"]
    assert all({"trait_id", "title", "description", "category", "confidence", "source"} <= set(t) for t in d["user_traits"])
    assert d["is_empty"] is False
    assert d["flow_node"] is None  # sin ConversationStep no hay flujo


def test_compile_marks_empty_when_no_domain_or_rule_atoms(tmp_path: Path) -> None:
    root = seed_store(tmp_path / "solo_tool", [a for a in minimal_business_atoms() if a["type"] == "tool"])
    d = compile_context(question="¿Promos?", user_id=None, knowledge=KnowledgeOperations(kb_root=root), trigger="cron").to_dict()
    assert d["domain_facts"] == [] and d["rules"] == []
    assert d["is_empty"] is True
    assert d["user_traits"] == []
    assert d["tools"][0]["name"] == "crear_reserva"  # la tool sigue disponible


def test_scenario_resolution_argument_then_session_then_loader_then_default(business_root: Path) -> None:
    reader = KnowledgeOperations(kb_root=business_root)
    compiler = ContextCompiler(knowledge=reader, session_state_loader=lambda uid: SessionStateStub(active_domain="cargado"))

    assert compiler.compile(question="q", user_id=1, scenario="arg").scenario == "arg"
    assert compiler.compile(question="q", user_id=1, session_state=SessionStateStub(active_domain="sesion")).scenario == "sesion"
    assert compiler.compile(question="q", user_id=1).scenario == "cargado"
    # cron no consulta el loader; cae al rotulo derivado de los tags domain:* (primer top-level)
    assert compiler.compile(question="", user_id=1, trigger="cron").scenario == "catalogo"


def test_graph_resolves_flow_node_transitions_and_grounding(negocio_kb: Path) -> None:
    compiler = ContextCompiler(knowledge=KnowledgeOperations(kb_root=negocio_kb))

    fresh = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub())
    assert fresh.flow_node == "conversation:steps.onboarding"  # default: onboarding
    assert fresh.allowed_transitions == ["conversation:steps.booking"]
    assert "step-onboarding" in fresh.grounding_atoms
    # El step activo viaja resuelto (instrucciones/slots) para el prompt del Conversador.
    assert fresh.step["tag"] == "conversation:steps.onboarding" and fresh.step["id"] == "step-onboarding"
    assert fresh.step["instructions"] and "instructions" in fresh.to_dict()["step"]
    assert compiler.step_context("conversation:steps.booking")["id"] == "step-booking"
    assert compiler.step_context("conversation:steps.inexistente") is None and compiler.step_context(None) is None

    in_booking = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.booking"))
    assert in_booking.flow_node == "conversation:steps.booking"
    assert in_booking.allowed_transitions == ["conversation:steps.onboarding"]
    assert {"step-booking", "tool-reserva"} <= set(in_booking.grounding_atoms)

    unknown = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.inexistente"))
    assert unknown.flow_node == "conversation:steps.onboarding"


def _step(step_id: str, tag: str) -> dict:
    return {
        "type": "step", "id": step_id, "title": step_id, "kind": "interaccion_simple",
        "tags": [f"conversation:steps.{tag}", "system:test"], "domain_ref": "test-biz",
        "fields": {"instructions": "x", "required_slots": "ninguno", "handout_target": "", "completion_condition": ""},
    }


def _edge(src: str, dst: str) -> dict:
    return {"type": "transitions_to", "source": src, "target": dst}


def test_entry_step_is_graph_root_when_kb_has_no_onboarding(tmp_path: Path) -> None:
    # saludo -> calificacion -> cierre. Alfabeticamente 'agendar' y 'calificacion'
    # van antes que 'saludo': el step de entrada tiene que salir del grafo, no
    # del orden de los tags (bug real de Vitali: arrancaba en agendar_visita).
    atoms = [a for a in minimal_business_atoms() if a["type"] == "domain"] + [
        _step("step-saludo", "saludo"), _step("step-calificacion", "calificacion"),
        _step("step-agendar", "agendar"), _step("step-cierre", "cierre"),
    ]
    root = seed_store(tmp_path / "flujo", atoms, relations=[
        _edge("step-saludo", "step-calificacion"), _edge("step-saludo", "step-agendar"),
        _edge("step-calificacion", "step-agendar"), _edge("step-agendar", "step-cierre"),
    ])
    compiler = ContextCompiler(knowledge=KnowledgeOperations(kb_root=root))
    fresh = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub())
    assert fresh.flow_node == "conversation:steps.saludo"
    assert fresh.allowed_transitions == ["conversation:steps.agendar", "conversation:steps.calificacion"] or \
        fresh.allowed_transitions == ["conversation:steps.calificacion", "conversation:steps.agendar"]

    # Una sesion con step valido no se toca; una con step inexistente vuelve a la raiz.
    assert compiler.compile(question="q", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.cierre")).flow_node == "conversation:steps.cierre"
    assert compiler.compile(question="q", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.nada")).flow_node == "conversation:steps.saludo"


def test_real_negocio_kb_compiles_full_business_context(negocio_kb: Path) -> None:
    d = compile_context(question="que pizzas hay?", user_id=None, knowledge=KnowledgeOperations(kb_root=negocio_kb)).to_dict()
    assert {"domain-menu", "domain-horarios", "domain-promos", "domain-ubicacion"} == {f["id"] for f in d["domain_facts"]}
    assert {r["id"] for r in d["rules"]} == {"rule-reservas"}
    assert d["persona"]["whoami"].startswith("Soy el asistente de la pizzeria")
    assert d["fallback_text"].startswith("Si no hay contexto suficiente")
    assert [t["name"] for t in d["tools"]] == ["crear_reserva"]
    assert d["is_empty"] is False


def test_tools_are_scoped_by_uses_tool_edges_of_the_reachable_steps(tmp_path: Path) -> None:
    """saludo -> calificacion -> cierre; solo calificacion usa la tool. Desde saludo la
    tool entra (calificacion es transicion permitida); desde cierre (terminal) no.
    Medido en el REPL: sin este alcance, el orquestador llamaba agendar_recordatorio
    desde despedida, un step terminal sin transiciones."""
    atoms = minimal_business_atoms(with_tool=True) + [
        _step("step-saludo", "saludo"), _step("step-calificacion", "calificacion"), _step("step-cierre", "cierre"),
    ]
    root = seed_store(tmp_path / "scoped", atoms, relations=[
        _edge("step-saludo", "step-calificacion"), _edge("step-calificacion", "step-cierre"),
        {"type": "uses_tool", "source": "step-calificacion", "target": "tool-reserva"},
    ])
    compiler = ContextCompiler(knowledge=KnowledgeOperations(kb_root=root))
    at_saludo = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.saludo"))
    assert [t["name"] for t in at_saludo.tools] == ["crear_reserva"]
    at_cierre = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.cierre"))
    assert at_cierre.tools == []


def test_tools_stay_unscoped_when_the_kb_declares_no_uses_tool(tmp_path: Path) -> None:
    atoms = minimal_business_atoms(with_tool=True) + [_step("step-saludo", "saludo"), _step("step-cierre", "cierre")]
    root = seed_store(tmp_path / "unscoped", atoms, relations=[_edge("step-saludo", "step-cierre")])
    compiler = ContextCompiler(knowledge=KnowledgeOperations(kb_root=root))
    at_cierre = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.cierre"))
    assert [t["name"] for t in at_cierre.tools] == ["crear_reserva"]
