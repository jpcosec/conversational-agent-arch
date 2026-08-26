from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.ontologizador.compiler import compile_context
from kb_agent.ontologizador.sldb_reader import SLDBReader


REPO_ROOT = Path(__file__).resolve().parents[1]
DONPEPPE_KB_ROOT = REPO_ROOT / ".sldb_e2e_donpeppe"


@dataclass
class SessionStateStub:
    active_domain: str | None = None


@pytest.fixture()
def seeded_business_root(tmp_path: Path) -> Path:
    """KB de un ÚNICO negocio (doctrina: una KB = un negocio).

    Los átomos llevan ejes semánticos independientes (self:*, conversation:*,
    domain:*), pero se seleccionan por ``atom_type`` porque TODOS pertenecen a
    este único negocio; no se filtran por un scenario string.
    """
    return _seed_store(
        tmp_path / "negocio",
        atoms=[
            {
                "id": "self-whoami",
                "title": "Self Whoami",
                "tags": ["atom_type:domain", "self:whoami", "source:manual"],
                "answer": "Soy el asistente de la pizzeria.",
            },
            {
                "id": "self-estilo",
                "title": "Self Estilo",
                "tags": ["atom_type:rule", "self:estilo", "source:manual"],
                "answer": "Responde breve y amable.",
            },
            {
                "id": "conversation-fallback",
                "title": "Conversation Fallback",
                "tags": ["atom_type:rule", "conversation:fallback", "source:manual"],
                "answer": "Si no hay contexto suficiente, pide una aclaración.",
            },
            {
                "id": "domain-menu",
                "title": "Domain Menu",
                "tags": ["atom_type:domain", "domain:catalogo", "source:e2e"],
                "answer": "La pizza margarita cuesta 10.",
            },
            {
                "id": "domain-horarios",
                "title": "Domain Horarios",
                "tags": ["atom_type:domain", "domain:horarios", "source:e2e"],
                "answer": "Atendemos de 12:00 a 23:00.",
            },
            {
                "id": "domain-regla-reservas",
                "title": "Domain Regla Reservas",
                "tags": ["atom_type:rule", "domain:reglas.reservas", "source:e2e"],
                "answer": "Las reservas requieren confirmación previa.",
            },
            {
                "id": "tool-reserva",
                "title": "Tool Reserva",
                "tags": ["atom_type:tool", "conversation:steps.booking", "self:tools"],
                "answer": "```json\n{\n  \"name\": \"crear_reserva\",\n  \"parameters\": {\n    \"type\": \"object\",\n    \"properties\": {\n      \"fecha\": {\"type\": \"string\"}\n    },\n    \"required\": [\"fecha\"]\n  }\n}\n```",
            },
        ],
    )


@pytest.fixture()
def seeded_empty_business_root(tmp_path: Path) -> Path:
    """KB sin átomos domain/rule: solo un tool. Debe compilar como is_empty."""
    return _seed_store(
        tmp_path / "solo_tool",
        atoms=[
            {
                "id": "tool-solo",
                "title": "Tool Solo",
                "tags": ["atom_type:tool", "self:tools"],
                "answer": json.dumps({"name": "noop", "parameters": {"type": "object"}}),
            },
        ],
    )


@pytest.fixture()
def identity_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        user = Users(external_id="wa:+56999999999", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add_all(
            [
                UserTraits(user_id=user.id, trait_id="trait-vegetariano", confidence=0.9, source="test"),
                UserTraits(user_id=user.id, trait_id="trait-prefiere-borde-relleno", confidence=0.7, source="test"),
            ]
        )
        session.commit()
        yield session
    finally:
        session.close()


def test_compile_context_selects_all_business_atoms_by_type(
    seeded_business_root: Path,
    identity_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctrina nueva: una KB = un negocio, contexto estructurado por rol.

    El compilador trae TODOS los atom_type:domain y atom_type:rule del negocio,
    pero los CLASIFICA por eje semantico: self:* va a persona, conversation:*
    va a strategy/fallback, y domain:* queda como grounding del negocio
    (domain_facts/rules). Asi el conversador no hardcodea identidad ni fallback.
    """
    llm_calls: list[object] = []

    class ForbiddenLLM:
        def __init__(self, *args, **kwargs) -> None:
            llm_calls.append({"args": args, "kwargs": kwargs})
            raise AssertionError("LLM usage is forbidden in context compiler tests")

    monkeypatch.setattr("google.adk.agents.LlmAgent", ForbiddenLLM)

    user_id = identity_session.query(Users.id).scalar()
    payload = compile_context(
        question="¿Qué opciones vegetarianas tienen y hasta qué hora atienden?",
        user_id=user_id,
        scenario=None,
        trigger="user",
        session_state=SessionStateStub(active_domain=None),
        reader=SLDBReader(kb_root=seeded_business_root, store_name=".sldb_test"),
        identity_session=identity_session,
    )

    d = payload.to_dict()

    # domain_facts: SOLO grounding del negocio (self:whoami se va a persona).
    # Trae id/body + tags/title para que el orquestador arme el turno sin re-leer (brecha #2).
    assert [{"id": f["id"], "body": f["body"]} for f in d["domain_facts"]] == [
        {"id": "domain-horarios", "body": "Atendemos de 12:00 a 23:00."},
        {"id": "domain-menu", "body": "La pizza margarita cuesta 10."},
    ]
    assert all("tags" in f and "title" in f for f in d["domain_facts"])
    # rules: SOLO grounding del negocio (self:estilo y conversation:fallback se separan)
    assert [{"id": r["id"], "body": r["body"]} for r in d["rules"]] == [
        {"id": "domain-regla-reservas", "body": "Las reservas requieren confirmación previa."},
    ]
    assert all("tags" in r and "title" in r for r in d["rules"])
    # persona: identidad del agente desde self:* (deshardcodeo del prompt)
    assert d["persona"] == {
        "whoami": "Soy el asistente de la pizzeria.",
        "estilo": "Responde breve y amable.",
    }
    # fallback: texto desde conversation:fallback (deshardcodeo del fallback)
    assert d["fallback_text"] == "Si no hay contexto suficiente, pide una aclaración."
    # tools: schema JSON del atom_type:tool
    assert d["tools"] == [
        {
            "name": "crear_reserva",
            "parameters": {
                "type": "object",
                "properties": {"fecha": {"type": "string"}},
                "required": ["fecha"],
            },
        }
    ]
    # traits resueltos contra SQL
    assert d["user_traits"] == ["trait-prefiere-borde-relleno", "trait-vegetariano"]
    assert d["is_empty"] is False
    assert d["question"] == "¿Qué opciones vegetarianas tienen y hasta qué hora atienden?"
    assert d.get("grounding_atoms") == []
    assert d.get("flow_node") is None
    assert llm_calls == []


def test_compile_context_marks_empty_when_kb_has_no_domain_or_rule_atoms(
    seeded_empty_business_root: Path,
) -> None:
    """is_empty=True cuando la KB no tiene átomos domain/rule que fundamenten."""
    payload = compile_context(
        question="¿Qué promociones tienen?",
        user_id=None,
        scenario=None,
        trigger="cron",
        reader=SLDBReader(kb_root=seeded_empty_business_root, store_name=".sldb_test"),
    )

    d = payload.to_dict()
    assert d["domain_facts"] == []
    assert d["rules"] == []
    assert d["is_empty"] is True
    assert d["user_traits"] == []
    # el tool sigue disponible aunque no haya facts/rules
    assert d["tools"] == [{"name": "noop", "parameters": {"type": "object"}}]


def test_compile_context_donpeppe_real_kb() -> None:
    """Validación con la KB REAL de Don Peppe reestructurada según la doctrina.

    Con la KB nueva (tags domain:catalogo / domain:horarios / domain:reglas.reservas)
    el compilador debe traer los facts y reglas del negocio sin depender del viejo
    scenario == domain:pizzeria.
    """
    if not DONPEPPE_KB_ROOT.exists():
        pytest.skip("KB Don Peppe no disponible en este entorno")

    payload = compile_context(
        question="que pizzas hay?",
        user_id=None,
        scenario=None,
        trigger="user",
        reader=SLDBReader(kb_root=DONPEPPE_KB_ROOT, store_name=".sldb"),
    )

    d = payload.to_dict()
    fact_ids = {f["id"] for f in d["domain_facts"]}
    rule_ids = {r["id"] for r in d["rules"]}

    assert "atom-donpeppe-carta" in fact_ids
    assert "atom-donpeppe-horarios" in fact_ids
    assert "atom-donpeppe-regla-reservas" in rule_ids
    assert d["is_empty"] is False


def _seed_store(root: Path, atoms: list[dict[str, object]]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _run(["sldb", "stores", "init", "--path", str(root)])
    store = root / ".sldb"
    _run(
        [
            "sldb",
            "models",
            "add",
            "deskops.models:AtomDoc",
            "--store",
            str(store),
            "--pythonpath",
            str(REPO_ROOT),
        ]
    )

    for atom in atoms:
        payload_path = root / f"{atom['id']}.yaml"
        payload_path.write_text(_atom_payload(atom), encoding="utf-8")
        output_path = root / "atoms" / f"{atom['id']}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                "sldb",
                "docs",
                "create",
                "--model",
                "AtomDoc",
                "-o",
                str(output_path),
                str(payload_path),
                "--store",
                str(store),
                "--pythonpath",
                str(REPO_ROOT),
            ]
        )

    os.symlink(store, root / ".sldb_test", target_is_directory=True)
    return root


def _atom_payload(atom: dict[str, object]) -> str:
    answer = str(atom["answer"])
    indented_answer = "\n".join(f"  {line}" if line else "" for line in answer.splitlines())
    tags = "\n".join(f"  - {tag}" for tag in atom["tags"])
    return (
        f"id: {atom['id']}\n"
        f"title: {atom['title']}\n"
        "five_wh_one_plus: what\n"
        "tags:\n"
        f"{tags}\n"
        "provenance: null\n"
        "answer: |\n"
        f"{indented_answer}\n"
    )


def _run(command: list[str]) -> None:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) if not pythonpath else f"{REPO_ROOT}{os.pathsep}{pythonpath}"
    subprocess.run(
        command,
        check=True,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
