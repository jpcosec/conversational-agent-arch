"""Unit tests for the knowledge_base CLI operations.

Seeds a small KB store with the new SLDB models and tests each
operation: explore, show, step_next, traits, self_context, context, propose.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from knowledge_base.operations import KnowledgeOperations
from kb_agent.models_sql.identity import Base, Users, UserTraits
from kb_agent.models_sql.session import SessionState, SessionNode


# ─────────────────────────── fixtures ───────────────────────────

MODELS = [
    "DomainAtom", "RuleAtom", "ToolAtom", "TraitAtom", "ConversationStep",
    "SelfDeclaration", "StyleGuide", "CapabilityBoundary", "StrategyRule", "FallbackRule",
]

ATOMS = [
    ("self-bot", "SelfDeclaration", """---
id: self-bot
title: Bot Identity
atom_type: self
tags:
- self:whoami
- system:test
provenance: null
---

# Bot Identity

## Statement

Soy un bot de prueba para el sistema de conocimiento.
"""),
    ("style-bot", "StyleGuide", """---
id: style-bot
title: Bot Style
atom_type: style
tags:
- self:estilo
- system:test
provenance: null
---

# Bot Style

## Tone

Amable y conciso.

## Language Register

Formal, trato de usted.

## Phrase Preferences



## Length Guidelines


"""),
    ("boundary-bot", "CapabilityBoundary", """---
id: boundary-bot
title: Bot Limits
atom_type: boundary
tags:
- self:limites
- system:test
provenance: null
---

# Bot Limits

## Restriction

No puedo dar consejo legal.

## Conditions



## Escalation

Derivar a un abogado.
"""),
    ("atom-carta", "DomainAtom", """---
id: atom-carta
title: Carta
atom_type: domain
tags:
- domain:catalogo
- system:test
five_wh_one_plus: what
domain_ref: test-biz
provenance: null
---

# Carta

## Answer

Pizza Margherita 8900, Napolitana 9800.
"""),
    ("trait-vegetariano", "TraitAtom", """---
id: trait-vegetariano
title: Vegetariano
atom_type: trait
tags:
- user:traits.vegetariano
- system:test
category: dietary
provenance: null
---

# Vegetariano

## Description

Cliente que no consume carne.
"""),
    ("step-onboarding", "ConversationStep", """---
id: step-onboarding
title: Onboarding
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.onboarding
- system:test
domain_ref: test-biz
---

# Onboarding

## Instructions

Dar la bienvenida.

## Required Slots

nombre

## Allowed Transitions

conversation:steps.booking

## Grounding Atoms

atom-carta

## Completion Condition

Usuario saludado.
"""),
]


@pytest.fixture(scope="module")
def kb_store(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed a KB store with the new models and atoms (module-scoped, read-only)."""
    kb_root = tmp_path_factory.mktemp("kb")
    _run(["sldb", "stores", "init", "--path", str(kb_root)])
    store = kb_root / ".sldb"

    for model in MODELS:
        _run([
            "sldb", "models", "add", f"kb_agent.models.knowledge:{model}",
            "--store", str(store), "--pythonpath", str(REPO_ROOT),
        ])

    atoms_dir = kb_root / "atoms"
    atoms_dir.mkdir(parents=True, exist_ok=True)
    for atom_id, model, content in ATOMS:
        atom_path = atoms_dir / f"{atom_id}.md"
        atom_path.write_text(content, encoding="utf-8")
        _run([
            "sldb", "docs", "track", str(atom_path.resolve()),
            "--model", model, "--store", str(store), "--pythonpath", str(REPO_ROOT),
        ])

    _run([
        "sldb", "stores", "update", "--store", str(store), "--pythonpath", str(REPO_ROOT),
    ])
    return kb_root


@pytest.fixture()
def seeded_db(tmp_path: Path) -> str:
    """Create a SQL db with a user, session state, and traits."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(SessionState(
            user_id=user.id,
            current_node=SessionNode.IDLE,
            flow_node="conversation:steps.onboarding",
            flow_slots={"missing_slots": ["nombre"]},
        ))
        session.add(UserTraits(
            user_id=user.id, trait_id="trait-vegetariano",
            confidence=0.9, source="perfilador",
        ))
        session.commit()
    finally:
        session.close()
    engine.dispose()
    return db_url


def _ops(kb_store: Path, db_url: str | None = None) -> KnowledgeOperations:
    return KnowledgeOperations(kb_store, db_url, pythonpath=str(REPO_ROOT))


# ─────────────────────────── explore ───────────────────────────

def test_explore_root_lists_entry_points(kb_store: Path) -> None:
    ops = _ops(kb_store)
    result = ops.explore()
    assert result["mode"] == "root"
    tags = {r["tag"] for r in result["root_tags"]}
    assert "system:test" in tags


def test_explore_tag_shows_children(kb_store: Path) -> None:
    ops = _ops(kb_store)
    result = ops.explore(tag="conversation:steps")
    assert result["mode"] == "tag"
    assert "conversation:steps.onboarding" in result["children"]


def test_explore_tag_leaf_lists_docs(kb_store: Path) -> None:
    ops = _ops(kb_store)
    result = ops.explore(tag="conversation:steps.onboarding")
    assert "step-onboarding" in result["docs"]


def test_explore_atom_shows_tags_and_siblings(kb_store: Path) -> None:
    ops = _ops(kb_store)
    result = ops.explore(atom="step-onboarding")
    assert result["mode"] == "atom"
    assert "conversation:steps.onboarding" in result["tags"]
    assert not any(t.startswith(("type.", "workspace.")) for t in result["tags"])


# ─────────────────────────── show ───────────────────────────

def test_show_returns_complete_atom(kb_store: Path) -> None:
    ops = _ops(kb_store)
    doc = ops.show("self-bot")
    assert doc is not None
    assert doc["id"] == "self-bot"
    assert doc["_model"] == "SelfDeclaration"
    assert "bot de prueba" in doc["statement"]


def test_show_returns_none_for_missing(kb_store: Path) -> None:
    ops = _ops(kb_store)
    assert ops.show("does-not-exist") is None


def test_show_tool_atom_has_parameters_field(kb_store: Path) -> None:
    ops = _ops(kb_store)
    doc = ops.show("atom-carta")
    assert doc is not None
    assert doc["_model"] == "DomainAtom"
    assert "answer" in doc


# ─────────────────────────── step next ───────────────────────────

def test_step_next_reads_flow_node_from_sql(kb_store: Path, seeded_db: str) -> None:
    ops = _ops(kb_store, seeded_db)
    result = ops.step_next("wa:+56900000000")
    assert result["flow_node"] == "conversation:steps.onboarding"
    assert result["missing_slots"] == ["nombre"]


def test_step_next_falls_back_without_sql(kb_store: Path) -> None:
    ops = _ops(kb_store)
    result = ops.step_next("unknown-user")
    # should fallback to semantic search for a step
    assert result["flow_node"] is not None


def test_step_next_unknown_user_returns_fallback(kb_store: Path, seeded_db: str) -> None:
    ops = _ops(kb_store, seeded_db)
    result = ops.step_next("wa:+56999999999")  # not in db
    assert "flow_node" in result


# ─────────────────────────── traits ───────────────────────────

def test_traits_resolves_from_sql_and_sldb(kb_store: Path, seeded_db: str) -> None:
    ops = _ops(kb_store, seeded_db)
    traits = ops.traits("wa:+56900000000")
    assert len(traits) == 1
    assert traits[0]["trait_id"] == "trait-vegetariano"
    assert traits[0]["title"] == "Vegetariano"
    assert traits[0]["category"] == "dietary"
    assert traits[0]["confidence"] == 0.9


def test_traits_empty_for_unknown_user(kb_store: Path, seeded_db: str) -> None:
    ops = _ops(kb_store, seeded_db)
    assert ops.traits("wa:+56999999999") == []


def test_traits_empty_without_sql(kb_store: Path) -> None:
    ops = _ops(kb_store)
    assert ops.traits("wa:+56900000000") == []


# ─────────────────────────── self ───────────────────────────

def test_self_context_compiles_three_categories(kb_store: Path) -> None:
    ops = _ops(kb_store)
    result = ops.self_context()
    assert len(result["identity"]) == 1
    assert len(result["style"]) == 1
    assert len(result["boundaries"]) == 1
    assert result["identity"][0]["id"] == "self-bot"
    assert result["style"][0]["tone"] == "Amable y conciso."
    assert "consejo legal" in result["boundaries"][0]["restriction"]


# ─────────────────────────── context ───────────────────────────

def test_context_aggregates_all(kb_store: Path, seeded_db: str) -> None:
    ops = _ops(kb_store, seeded_db)
    result = ops.context("wa:+56900000000")
    assert set(result.keys()) == {"step", "traits", "self"}
    assert result["step"]["flow_node"] == "conversation:steps.onboarding"
    assert len(result["traits"]) == 1
    assert len(result["self"]["identity"]) == 1


# ─────────────────────────── propose ───────────────────────────

def test_propose_creates_atom_with_proposed_status(kb_store: Path, tmp_path: Path) -> None:
    # Use an isolated copy so we don't pollute the module-scoped store
    import shutil
    isolated = tmp_path / "kb_propose"
    shutil.copytree(kb_store, isolated)
    ops = _ops(isolated)
    result = ops.propose("domain", """
id: atom-nueva-propuesta
title: Nueva Propuesta
five_wh_one_plus: what
answer: Contenido propuesto
tags:
- domain:test
""")
    assert result["status"] == "proposed"
    assert result["source"] == "reflector"
    atom_path = Path(result["path"])
    assert atom_path.exists()
    content = atom_path.read_text(encoding="utf-8")
    assert "status:proposed" in content
    assert "source:reflector" in content


def test_propose_rejects_unknown_model(kb_store: Path) -> None:
    ops = _ops(kb_store)
    with pytest.raises(ValueError, match="Unknown model"):
        ops.propose("nonexistent", "id: x\ntitle: y")


def test_propose_rejects_non_dict_body(kb_store: Path) -> None:
    ops = _ops(kb_store)
    with pytest.raises(ValueError, match="must be a YAML"):
        ops.propose("domain", "just a string")


# ─────────────────────────── helpers ───────────────────────────

def _run(command: list[str]) -> None:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) if not pythonpath else f"{REPO_ROOT}{os.pathsep}{pythonpath}"
    subprocess.run(
        command, check=True, cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=60,
    )