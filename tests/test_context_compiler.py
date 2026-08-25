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


@dataclass
class SessionStateStub:
    active_domain: str | None = None


@pytest.fixture()
def seeded_pizzeria_root(tmp_path: Path) -> Path:
    return _seed_store(
        tmp_path / "pizzeria",
        atoms=[
            {
                "id": "rule-pizza-respuesta-breve",
                "title": "Rule Pizza Respuesta Breve",
                "tags": ["atom_type:rule", "topic:rules", "domain:pizza"],
                "answer": "Responde solo con información confirmada del local.",
            },
            {
                "id": "domain-pizza-menu",
                "title": "Domain Pizza Menu",
                "tags": ["atom_type:domain", "topic:ontology", "domain:pizza"],
                "answer": "La pizza margarita cuesta 10.",
            },
            {
                "id": "domain-pizza-horarios",
                "title": "Domain Pizza Horarios",
                "tags": ["atom_type:domain", "topic:ontology", "domain:pizza.horarios"],
                "answer": "Atendemos de 12:00 a 23:00.",
            },
            {
                "id": "tool-pizza-order-status",
                "title": "Tool Pizza Order Status",
                "tags": ["atom_type:tool", "topic:tool-calling", "domain:pizza"],
                "answer": "```json\n{\n  \"name\": \"lookup_order\",\n  \"parameters\": {\n    \"type\": \"object\",\n    \"properties\": {\n      \"order_id\": {\"type\": \"string\"}\n    },\n    \"required\": [\"order_id\"]\n  }\n}\n```",
            },
            {
                "id": "rule-farmacia-recetas",
                "title": "Rule Farmacia Recetas",
                "tags": ["atom_type:rule", "topic:rules", "domain:farmacia"],
                "answer": "No dispensar antibióticos sin receta.",
            },
            {
                "id": "domain-farmacia-stock",
                "title": "Domain Farmacia Stock",
                "tags": ["atom_type:domain", "topic:ontology", "domain:farmacia"],
                "answer": "Hay stock de analgésicos.",
            },
            {
                "id": "tool-farmacia-delivery",
                "title": "Tool Farmacia Delivery",
                "tags": ["atom_type:tool", "topic:tool-calling", "domain:farmacia"],
                "answer": json.dumps({"name": "book_delivery", "parameters": {"type": "object"}}),
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


def test_compile_context_filters_only_matching_domain_atoms(
    seeded_pizzeria_root: Path,
    identity_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        session_state=SessionStateStub(active_domain="pizza"),
        reader=SLDBReader(kb_root=seeded_pizzeria_root, store_name=".sldb_test"),
        identity_session=identity_session,
    )

    d = payload.to_dict()
    expected = {
        "scenario": "pizza",
        "question": "¿Qué opciones vegetarianas tienen y hasta qué hora atienden?",
        "user_traits": ["trait-prefiere-borde-relleno", "trait-vegetariano"],
        "rules": [
            {"id": "rule-pizza-respuesta-breve", "body": "Responde solo con información confirmada del local."},
        ],
        "domain_facts": [
            {"id": "domain-pizza-horarios", "body": "Atendemos de 12:00 a 23:00."},
            {"id": "domain-pizza-menu", "body": "La pizza margarita cuesta 10."},
        ],
        "tools": [
            {
                "name": "lookup_order",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            }
        ],
        "is_empty": False,
    }
    for k, v in expected.items():
        assert d.get(k) == v, f"field {k!r} mismatch"
    assert d.get("grounding_atoms") == []
    assert d.get("flow_node") is None
    assert llm_calls == []


def test_compile_context_marks_empty_when_scenario_has_no_atoms(seeded_pizzeria_root: Path) -> None:
    payload = compile_context(
        question="¿Qué promociones tienen?",
        user_id=None,
        scenario="biblioteca",
        trigger="cron",
        reader=SLDBReader(kb_root=seeded_pizzeria_root, store_name=".sldb_test"),
    )

    d = payload.to_dict()
    assert d == {
        "scenario": "biblioteca",
        "question": "¿Qué promociones tienen?",
        "user_traits": [],
        "rules": [],
        "domain_facts": [],
        "tools": [],
        "is_empty": True,
        "grounding_atoms": [],
        "flow_node": None,
        "allowed_transitions": [],
        "missing_slots": [],
        "system_turn": None,
    }


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
