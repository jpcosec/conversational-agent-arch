from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from kb_agent.ontologizador.sldb_reader import SLDBReader


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def seeded_roots(tmp_path: Path) -> tuple[Path, Path]:
    root_a = _seed_store(
        tmp_path / "domain_a",
        atoms=[
            {
                "id": "atom-tool-calendar",
                "title": "Calendar Tool",
                "tags": ["atom_type:tool", "topic:tool-calling", "channel:calendar"],
                "answer": json.dumps(
                    {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "service": {"type": "string"},
                        },
                        "required": ["date"],
                    }
                ),
            },
            {
                "id": "atom-rule-cancelacion",
                "title": "Rule Cancelacion",
                "tags": ["atom_type:rule", "topic:rules"],
                "answer": "Cancelar con menos de 24h requiere penalidad.",
            },
            {
                "id": "atom-domain-horarios",
                "title": "Domain Horarios",
                "tags": ["atom_type:domain", "topic:ontology"],
                "answer": "Lunes a viernes de 09:00 a 18:00.",
            },
            {
                "id": "trait-paciente-frecuente",
                "title": "Trait Paciente Frecuente",
                "tags": ["atom_type:trait", "topic:profiling"],
                "answer": "Ofrecer descuento por recurrencia.",
            },
        ],
    )
    root_b = _seed_store(
        tmp_path / "domain_b",
        atoms=[
            {
                "id": "atom-tool-weather",
                "title": "Weather Tool",
                "tags": ["atom_type:tool", "topic:tool-calling", "channel:weather"],
                "answer": "A function to get weather by city.",
            },
            {
                "id": "atom-domain-clima",
                "title": "Domain Clima",
                "tags": ["atom_type:domain", "topic:ontology"],
                "answer": "Pronóstico por ciudad.",
            },
        ],
    )
    return root_a, root_b


def test_fetch_tool_returns_only_tool_atoms_with_schema(seeded_roots: tuple[Path, Path]) -> None:
    root_a, _ = seeded_roots
    reader = SLDBReader(kb_root=root_a, store_name=".sldb_test")
    atoms = reader.fetch("tool")
    assert atoms
    assert all("atom_type:tool" in a.get("tags", []) for a in atoms)
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