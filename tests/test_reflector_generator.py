from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kb_agent.reflector.generator import ReflectorAtomGenerator
from kb_agent.reflector.reader import ReflectorHistoryRow


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_generator_writes_proposed_reflector_atom_for_recurrent_pattern(tmp_path: Path) -> None:
    root = _seed_generator_root(tmp_path / "generator_root")
    generator = ReflectorAtomGenerator(
        kb_root=root,
        store_name=".sldb_test",
        output_dir=root / ".sldb_test" / "generated-atoms",
    )

    created = generator.generate(_recurrent_rows())

    assert len(created) == 1
    created_path = created[0].path
    assert created_path.exists()
    assert ".sldb_test" in str(created_path)
    content = created_path.read_text(encoding="utf-8")
    assert "- source:reflector" in content
    assert "status: proposed" in content
    assert "¿Cuál es el horario de atención?" in content


def test_generator_does_not_duplicate_existing_pattern(tmp_path: Path) -> None:
    root = _seed_generator_root(tmp_path / "generator_root")
    generator = ReflectorAtomGenerator(
        kb_root=root,
        store_name=".sldb_test",
        output_dir=root / ".sldb_test" / "generated-atoms",
    )

    first = generator.generate(_recurrent_rows())
    second = generator.generate(_recurrent_rows())

    generated_files = sorted((root / ".sldb_test" / "generated-atoms").glob("*.md"))
    assert len(first) == 1
    assert second == []
    assert len(generated_files) == 1


def _seed_generator_root(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "desk" / "atoms").mkdir(parents=True, exist_ok=True)
    (root / "desk" / "atoms" / "tag-namespaces.yaml").write_text(
        (
            "namespaces:\n"
            "  domain:\n"
            "    meaning: Problem domain or durable area of concern.\n"
            "    use_when: The atom belongs to a reusable problem domain.\n"
            "    do_not_use_when: A more specific tag applies.\n"
            "    examples:\n"
            "      - domain:knowledge-management\n"
            "  layer:\n"
            "    meaning: Architectural layer where the atom applies.\n"
            "    use_when: The atom is scoped to a layer of the system.\n"
            "    do_not_use_when: The tag names only a broad topic or system.\n"
            "    examples:\n"
            "      - layer:runtime\n"
            "  source:\n"
            "    meaning: Provenance channel or producer that originated the atom draft.\n"
            "    use_when: The atom is machine-generated and needs source attribution.\n"
            "    do_not_use_when: The tag expresses the atom subject instead of origin.\n"
            "    examples:\n"
            "      - source:reflector\n"
            "  system:\n"
            "    meaning: System, project, or tool the atom belongs to.\n"
            "    use_when: The atom is about a specific system.\n"
            "    do_not_use_when: The tag is only a general topic.\n"
            "    examples:\n"
            "      - system:deskops\n"
            "  topic:\n"
            "    meaning: Subject area discussed by the atom.\n"
            "    use_when: The atom is about a conceptual topic.\n"
            "    do_not_use_when: The atom describes a reusable implementation shape.\n"
            "    examples:\n"
            "      - topic:ontology\n"
            "      - topic:rules\n"
        ),
        encoding="utf-8",
    )

    _run(["sldb", "stores", "init", "--path", str(root)])
    os.rename(root / ".sldb", root / ".sldb_test")
    _run(
        [
            "sldb",
            "models",
            "add",
            "deskops.models:AtomDoc",
            "--store",
            str(root / ".sldb_test"),
            "--pythonpath",
            str(REPO_ROOT),
        ]
    )
    return root


def _recurrent_rows() -> list[ReflectorHistoryRow]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        ReflectorHistoryRow(
            id=index,
            user_id=100 + index,
            role="user",
            content="¿Cuál es el horario de atención?" if index % 2 else "¿Cuál es el horario de atención?! ",
            created_at=base + timedelta(minutes=index),
        )
        for index in range(1, 6)
    ]


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
