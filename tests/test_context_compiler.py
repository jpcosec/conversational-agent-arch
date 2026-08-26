from __future__ import annotations

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
DONPEPPE_KB_ROOT = REPO_ROOT / "tests" / "knowledge"


@dataclass
class SessionStateStub:
    active_domain: str | None = None


# ── modelos tipados usados en el seed ────────────────────────────────
#: mapea cada atom del seed a su modelo de kb_agent.models.knowledge
_MODEL_IMPORTS = {
    "self": "kb_agent.models.knowledge:SelfDeclaration",
    "style": "kb_agent.models.knowledge:StyleGuide",
    "boundary": "kb_agent.models.knowledge:CapabilityBoundary",
    "strategy": "kb_agent.models.knowledge:StrategyRule",
    "fallback": "kb_agent.models.knowledge:FallbackRule",
    "domain": "kb_agent.models.knowledge:DomainAtom",
    "rule": "kb_agent.models.knowledge:RuleAtom",
    "tool": "kb_agent.models.knowledge:ToolAtom",
    "trait": "kb_agent.models.knowledge:TraitAtom",
}
_MODEL_CLASS = {
    "self": "SelfDeclaration",
    "style": "StyleGuide",
    "boundary": "CapabilityBoundary",
    "strategy": "StrategyRule",
    "fallback": "FallbackRule",
    "domain": "DomainAtom",
    "rule": "RuleAtom",
    "tool": "ToolAtom",
    "trait": "TraitAtom",
}


@pytest.fixture()
def seeded_business_root(tmp_path: Path) -> Path:
    """KB tipada de un ÚNICO negocio (doctrina: una KB = un negocio).

    Los átomos se modelan con modelos tipados (SelfDeclaration, StyleGuide,
    FallbackRule, DomainAtom, RuleAtom, ToolAtom) y se seleccionan por
    ``type.knowledge.<tipo>``. Cada tipo aporta sus campos propios.
    """
    return _seed_store(
        tmp_path / "negocio",
        atoms=[
            {
                "type": "self",
                "id": "self-whoami",
                "title": "Self Whoami",
                "tags": ["self:whoami", "system:donpeppe"],
                "fields": {"statement": "Soy el asistente de la pizzeria."},
            },
            {
                "type": "style",
                "id": "style-donpeppe",
                "title": "Estilo",
                "tags": ["self:estilo", "system:donpeppe"],
                "fields": {
                    "tone": "Responde breve y amable.",
                    "language_register": "Español chileno, trato de tú.",
                    "phrase_preferences": "Frases cortas.",
                    "length_guidelines": "Bajo 300 caracteres.",
                },
            },
            {
                "type": "fallback",
                "id": "fallback-donpeppe",
                "title": "Fallback",
                "tags": ["conversation:fallback", "system:donpeppe"],
                "fields": {
                    "fallback_message": "Si no hay contexto suficiente, pide una aclaración.",
                    "conditions": "Cuando falta contexto.",
                },
            },
            {
                "type": "domain",
                "id": "domain-menu",
                "title": "Domain Menu",
                "tags": ["domain:catalogo", "system:donpeppe"],
                "five_wh": "what",
                "fields": {"answer": "La pizza margarita cuesta 10."},
            },
            {
                "type": "domain",
                "id": "domain-horarios",
                "title": "Domain Horarios",
                "tags": ["domain:horarios", "system:donpeppe"],
                "five_wh": "when",
                "fields": {"answer": "Atendemos de 12:00 a 23:00."},
            },
            {
                "type": "rule",
                "id": "domain-regla-reservas",
                "title": "Domain Regla Reservas",
                "tags": ["domain:reglas.reservas", "system:donpeppe"],
                "five_wh": "how",
                "fields": {
                    "answer": "Las reservas requieren confirmación previa.",
                    "conditions": "Aplica al reservar mesa.",
                },
            },
            {
                "type": "tool",
                "id": "tool-reserva",
                "title": "Tool Reserva",
                "tags": ["self:tools", "conversation:steps.booking", "system:donpeppe"],
                "fields": {
                    "description": "Crea una reserva.",
                    "parameters": '{"name": "crear_reserva", "parameters": {"type": "object", "properties": {"fecha": {"type": "string"}}, "required": ["fecha"]}}',
                },
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
                "type": "tool",
                "id": "tool-solo",
                "title": "Tool Solo",
                "tags": ["self:tools", "system:donpeppe"],
                "fields": {
                    "description": "No-op.",
                    "parameters": '{"name": "noop", "parameters": {"type": "object"}}',
                },
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
    """Doctrina tipada: una KB = un negocio, contexto estructurado por MODELO.

    El compilador selecciona por ``type.knowledge.<tipo>`` y arma persona desde
    SelfDeclaration/StyleGuide/CapabilityBoundary, strategy desde StrategyRule y
    fallback desde FallbackRule. domain/rule quedan como grounding del negocio.
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
        reader=SLDBReader(kb_root=seeded_business_root, store_name=".sldb"),
        identity_session=identity_session,
    )

    d = payload.to_dict()

    # domain_facts: grounding del negocio (DomainAtom.answer). Trae id/body + tags/title.
    assert [{"id": f["id"], "body": f["body"]} for f in d["domain_facts"]] == [
        {"id": "domain-horarios", "body": "Atendemos de 12:00 a 23:00."},
        {"id": "domain-menu", "body": "La pizza margarita cuesta 10."},
    ]
    assert all("tags" in f and "title" in f for f in d["domain_facts"])
    # rules: grounding del negocio (RuleAtom.answer)
    assert [{"id": r["id"], "body": r["body"]} for r in d["rules"]] == [
        {"id": "domain-regla-reservas", "body": "Las reservas requieren confirmación previa."},
    ]
    assert all("tags" in r and "title" in r for r in d["rules"])
    # persona: whoami desde SelfDeclaration.statement; estilo desde StyleGuide
    assert d["persona"]["whoami"] == "Soy el asistente de la pizzeria."
    assert "Responde breve y amable." in d["persona"]["estilo"]
    assert "Español chileno" in d["persona"]["estilo"]
    # fallback: texto desde FallbackRule.fallback_message
    assert d["fallback_text"] == "Si no hay contexto suficiente, pide una aclaración."
    # tools: schema JSON desde ToolAtom.parameters
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
        reader=SLDBReader(kb_root=seeded_empty_business_root, store_name=".sldb"),
    )

    d = payload.to_dict()
    assert d["domain_facts"] == []
    assert d["rules"] == []
    assert d["is_empty"] is True
    assert d["user_traits"] == []
    # el tool sigue disponible aunque no haya facts/rules
    assert d["tools"] == [{"name": "noop", "parameters": {"type": "object"}}]


def test_compile_context_donpeppe_real_kb() -> None:
    """Validación con la KB REAL tipada de Don Peppe (tests/knowledge)."""
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


# ── helpers de seed (KB tipada) ──────────────────────────────────────

def _seed_store(root: Path, atoms: list[dict[str, object]]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _run(["sldb", "stores", "init", "--path", str(root)])
    store = root / ".sldb"

    registered: set[str] = set()
    for atom in atoms:
        tipo = str(atom["type"])
        if tipo not in registered:
            _run(
                [
                    "sldb", "models", "add", _MODEL_IMPORTS[tipo],
                    "--store", str(store), "--pythonpath", str(REPO_ROOT),
                ]
            )
            registered.add(tipo)

        rel_path = Path("atoms") / f"{atom['id']}.md"
        out_path = root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_atom_markdown(atom), encoding="utf-8")
        _run(
            [
                "sldb", "docs", "track", str(rel_path),
                "--model", _MODEL_CLASS[tipo],
                "--store", str(store), "--pythonpath", str(REPO_ROOT),
            ]
        )

    _run(["sldb", "stores", "update", "--store", str(store), "--pythonpath", str(REPO_ROOT)])
    return root


def _atom_markdown(atom: dict[str, object]) -> str:
    tipo = str(atom["type"])
    tags = "\n".join(f"- {tag}" for tag in atom["tags"])  # type: ignore[union-attr]
    lines = [
        "---",
        f"id: {atom['id']}",
        f"title: {atom['title']}",
    ]
    if "five_wh" in atom:
        lines.append(f"five_wh_one_plus: {atom['five_wh']}")
    lines.append(f"atom_type: {tipo}")
    lines.append(f"summary: {atom.get('summary', atom['title'])}")
    lines.append("tags:")
    lines.append(tags)
    if tipo == "domain":
        lines.append("domain_ref: negocio")
    if tipo == "rule":
        lines.append("applies_to: negocio")
    if tipo == "trait":
        lines.append(f"category: {atom.get('category', 'general')}")
    lines.append("provenance: null")
    lines.append("---")
    lines.append("")
    lines.append(f"# {atom['title']}")
    lines.append("")
    # secciones por campo del modelo tipado
    fields: dict[str, str] = atom["fields"]  # type: ignore[assignment]
    section_titles = {
        "statement": "Statement",
        "tone": "Tone",
        "language_register": "Language Register",
        "phrase_preferences": "Phrase Preferences",
        "length_guidelines": "Length Guidelines",
        "fallback_message": "Fallback Message",
        "conditions": "Conditions",
        "answer": "Answer",
        "description": "Description",
        "parameters": "Parameters",
        "restriction": "Restriction",
        "escalation": "Escalation",
        "goal": "Goal",
        "approach": "Approach",
        "priorities": "Priorities",
    }
    for field, value in fields.items():
        lines.append(f"## {section_titles.get(field, field.title())}")
        lines.append("")
        if tipo == "tool" and field == "parameters":
            # ToolAtom espera el schema en un bloque ```json.
            lines.append("```json")
            lines.append(str(value))
            lines.append("```")
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


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
