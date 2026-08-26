from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from kb_agent.ontologizador.sldb_reader import SLDBReader


REPO_ROOT = Path(__file__).resolve().parents[1]

# modelos tipados usados en el seed
_MODEL_IMPORT = {
    "tool": "kb_agent.models.knowledge:ToolAtom",
    "rule": "kb_agent.models.knowledge:RuleAtom",
    "domain": "kb_agent.models.knowledge:DomainAtom",
    "trait": "kb_agent.models.knowledge:TraitAtom",
}
_MODEL_CLASS = {"tool": "ToolAtom", "rule": "RuleAtom", "domain": "DomainAtom", "trait": "TraitAtom"}


@pytest.fixture()
def seeded_roots(tmp_path: Path) -> tuple[Path, Path]:
    root_a = _seed_store(
        tmp_path / "domain_a",
        atoms=[
            {
                "type": "tool",
                "id": "atom-tool-calendar",
                "title": "Calendar Tool",
                "tags": ["self:tools", "channel:calendar"],
                "fields": {
                    "description": "Agenda una cita.",
                    "parameters": '{"name": "calendar", "parameters": {"type": "object", "properties": {"date": {"type": "string"}}, "required": ["date"]}}',
                },
            },
            {
                "type": "rule",
                "id": "atom-rule-cancelacion",
                "title": "Rule Cancelacion",
                "tags": ["domain:reglas.cancelacion", "system:clinica"],
                "five_wh": "how",
                "fields": {
                    "answer": "Cancelar con menos de 24h requiere penalidad.",
                    "conditions": "Al cancelar.",
                },
            },
            {
                "type": "domain",
                "id": "atom-domain-horarios",
                "title": "Domain Horarios",
                "tags": ["domain:horarios", "system:clinica"],
                "five_wh": "when",
                "fields": {"answer": "Lunes a viernes de 09:00 a 18:00."},
            },
            {
                "type": "trait",
                "id": "trait-paciente-frecuente",
                "title": "Trait Paciente Frecuente",
                "tags": ["user:traits.frecuente", "system:clinica"],
                "category": "loyalty",
                "fields": {"description": "Ofrecer descuento por recurrencia."},
            },
        ],
    )
    root_b = _seed_store(
        tmp_path / "domain_b",
        atoms=[
            {
                "type": "tool",
                "id": "atom-tool-weather",
                "title": "Weather Tool",
                "tags": ["self:tools", "channel:weather"],
                "fields": {
                    "description": "Consulta el clima.",
                    "parameters": '{"name": "weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}',
                },
            },
            {
                "type": "domain",
                "id": "atom-domain-clima",
                "title": "Domain Clima",
                "tags": ["domain:clima", "system:meteo"],
                "five_wh": "what",
                "fields": {"answer": "Pronóstico por ciudad."},
            },
        ],
    )
    return root_a, root_b


def test_fetch_tool_returns_only_tool_atoms_with_schema(seeded_roots: tuple[Path, Path]) -> None:
    root_a, _ = seeded_roots
    reader = SLDBReader(kb_root=root_a, store_name=".sldb_test")
    atoms = reader.fetch("tool")
    assert atoms
    # seleccion por MODELO tipado (ToolAtom): todos exponen el schema JSON.
    assert all(a.get("parameters") for a in atoms)
    assert len(atoms) == 1


def test_fetch_respects_kb_root_swap(seeded_roots: tuple[Path, Path]) -> None:
    root_a, root_b = seeded_roots
    tools_a = SLDBReader(kb_root=root_a, store_name=".sldb_test").fetch("tool")
    tools_b = SLDBReader(kb_root=root_b, store_name=".sldb_test").fetch("tool")
    ids_a = {a["id"] for a in tools_a}
    ids_b = {a["id"] for a in tools_b}
    assert ids_a == {"atom-tool-calendar"}
    assert ids_b == {"atom-tool-weather"}
    assert ids_a != ids_b


@pytest.mark.parametrize("atom_type,expected_id", [
    ("rule", "atom-rule-cancelacion"),
    ("domain", "atom-domain-horarios"),
    ("trait", "trait-paciente-frecuente"),
])
def test_fetch_supports_all_declared_atom_types(
    seeded_roots: tuple[Path, Path], atom_type: str, expected_id: str
) -> None:
    root_a, _ = seeded_roots
    reader = SLDBReader(kb_root=root_a, store_name=".sldb_test")
    atoms = reader.fetch(atom_type)
    assert [a["id"] for a in atoms] == [expected_id]


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
                    "sldb", "models", "add", _MODEL_IMPORT[tipo],
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
    os.symlink(store, root / ".sldb_test", target_is_directory=True)
    return root


def _atom_markdown(atom: dict[str, object]) -> str:
    tipo = str(atom["type"])
    tags = "\n".join(f"- {tag}" for tag in atom["tags"])  # type: ignore[union-attr]
    lines = ["---", f"id: {atom['id']}", f"title: {atom['title']}"]
    if "five_wh" in atom:
        lines.append(f"five_wh_one_plus: {atom['five_wh']}")
    lines.append(f"atom_type: {tipo}")
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
    section_titles = {
        "answer": "Answer",
        "conditions": "Conditions",
        "description": "Description",
        "parameters": "Parameters",
    }
    fields: dict[str, str] = atom["fields"]  # type: ignore[assignment]
    for field, value in fields.items():
        lines.append(f"## {section_titles.get(field, field.title())}")
        lines.append("")
        if tipo == "tool" and field == "parameters":
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
