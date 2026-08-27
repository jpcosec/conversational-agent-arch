"""Ontologizador: SLDB (modelos tipados) + SQL (traits) + KGDB (flujo) -> CompiledDocument."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.ontologizador.compiler import ContextCompiler, compile_context
from kb_agent.ontologizador.kgdb_reader import KGDBReader
from kb_agent.ontologizador.sldb_reader import SLDBReader
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
        reader=SLDBReader(kb_root=business_root),
        identity_session=identity_session,
        session_state=SessionStateStub(),
    ).to_dict()

    assert [(f["id"], f["body"]) for f in d["domain_facts"]] == [
        ("domain-horarios", "Atendemos de 12:00 a 23:00."),
        ("domain-menu", "La pizza margarita cuesta 10."),
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
    assert d["flow_node"] is None  # sin KGDB no hay flujo


def test_compile_marks_empty_when_no_domain_or_rule_atoms(tmp_path: Path) -> None:
    root = seed_store(tmp_path / "solo_tool", [a for a in minimal_business_atoms() if a["type"] == "tool"])
    d = compile_context(question="¿Promos?", user_id=None, reader=SLDBReader(kb_root=root), trigger="cron").to_dict()
    assert d["domain_facts"] == [] and d["rules"] == []
    assert d["is_empty"] is True
    assert d["user_traits"] == []
    assert d["tools"][0]["name"] == "crear_reserva"  # la tool sigue disponible


def test_scenario_resolution_argument_then_session_then_loader_then_default(business_root: Path) -> None:
    reader = SLDBReader(kb_root=business_root)
    compiler = ContextCompiler(reader=reader, session_state_loader=lambda uid: SessionStateStub(active_domain="cargado"))

    assert compiler.compile(question="q", user_id=1, scenario="arg").scenario == "arg"
    assert compiler.compile(question="q", user_id=1, session_state=SessionStateStub(active_domain="sesion")).scenario == "sesion"
    assert compiler.compile(question="q", user_id=1).scenario == "cargado"
    # cron no consulta el loader; cae al rotulo derivado de los tags domain:* (primer top-level)
    assert compiler.compile(question="", user_id=1, trigger="cron").scenario == "catalogo"


def test_kgdb_augments_flow_node_transitions_and_grounding(donpeppe_kb: Path) -> None:
    reader = SLDBReader(kb_root=donpeppe_kb)
    compiler = ContextCompiler(reader=reader, kgdb=KGDBReader.from_sldb(donpeppe_kb / ".sldb"))

    fresh = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub())
    assert fresh.flow_node == "conversation:steps.onboarding"  # default: onboarding
    assert fresh.allowed_transitions == ["conversation:steps.booking"]
    assert "step-donpeppe-onboarding" in fresh.grounding_atoms

    in_booking = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.booking"))
    assert in_booking.flow_node == "conversation:steps.booking"
    assert in_booking.allowed_transitions == ["conversation:steps.onboarding"]
    assert {"step-donpeppe-booking", "atom-donpeppe-tool-reserva"} <= set(in_booking.grounding_atoms)

    unknown = compiler.compile(question="hola", user_id=None, session_state=SessionStateStub(flow_node="conversation:steps.inexistente"))
    assert unknown.flow_node == "conversation:steps.onboarding"


def test_real_donpeppe_kb_compiles_full_business_context(donpeppe_kb: Path) -> None:
    d = compile_context(question="que pizzas hay?", user_id=None, reader=SLDBReader(kb_root=donpeppe_kb)).to_dict()
    assert {"atom-donpeppe-carta", "atom-donpeppe-horarios", "atom-donpeppe-promos", "atom-donpeppe-ubicacion"} == {f["id"] for f in d["domain_facts"]}
    assert {r["id"] for r in d["rules"]} == {"atom-donpeppe-regla-reservas"}
    assert d["persona"]["whoami"].startswith("Soy el asistente virtual de Don Peppe")
    assert d["fallback_text"].startswith("Uy, eso no lo tengo a mano")
    assert [t["name"] for t in d["tools"]] == ["crear_reserva"]
    assert d["is_empty"] is False
