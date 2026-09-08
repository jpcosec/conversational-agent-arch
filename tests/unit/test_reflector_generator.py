from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from kb_agent.reflector.generator import ReflectorAtomGenerator
from kb_agent.reflector.reader import ReflectorHistoryRow
from tests.support.sldb_seed import DEFAULT_NAMESPACES_REGISTRY, minimal_business_atoms, seed_store


def _generator(tmp_path: Path) -> tuple[ReflectorAtomGenerator, Path]:
    root = seed_store(tmp_path / "kb", minimal_business_atoms(), namespaces_registry=DEFAULT_NAMESPACES_REGISTRY)
    return ReflectorAtomGenerator(kb_root=root, registry_root=root), root


def test_generator_proposes_a_tracked_domain_atom_for_recurrent_pattern(tmp_path: Path) -> None:
    generator, root = _generator(tmp_path)
    created = generator.generate(_recurrent_rows())
    assert len(created) == 1
    created_path = created[0].path
    assert created_path.exists() and created_path.is_relative_to(root)
    content = created_path.read_text(encoding="utf-8")
    assert "- source:reflector" in content and "- status:proposed" in content
    assert "¿Cuál es el horario de atención?" in content
    # trackeado en el store: visible por el contrato de runtime, como cualquier DomainAtom
    proposed = [a for a in generator._knowledge.docs_by_type("domain") if a["id"] == created[0].atom_id]
    assert proposed and "status:proposed" in proposed[0]["tags"]


def test_generator_does_not_duplicate_existing_pattern(tmp_path: Path) -> None:
    generator, root = _generator(tmp_path)
    first = generator.generate(_recurrent_rows())
    second = generator.generate(_recurrent_rows())
    assert len(first) == 1 and second == []
    assert len([p for p in root.rglob("*.md") if "source:reflector" in p.read_text(encoding="utf-8")]) == 1


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
