"""Reflector cableado al orquestador: ChatHistory (scrubbed) -> atoms propuestos en la KB (copia)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from kb_agent.orchestrator import Orchestrator
from kb_agent.reflector import PATTERN_MIN_COUNT
from tests.support.fakes import offline_orchestrator

DELIVERY = ["¿Hacen delivery?", "hacen delivery?!", "Hacen delivery", "¿hacen delivery?", "Hacen delivery...", "HACEN DELIVERY"]


@pytest.fixture()
def kb_copy(tmp_path: Path, donpeppe_kb: Path) -> Path:
    copied = tmp_path / "knowledge"
    shutil.copytree(donpeppe_kb, copied, ignore=shutil.ignore_patterns(".embedding_cache"))
    return copied


def _seed_turns(orch: Orchestrator, external_id: str, messages: list[str]) -> None:
    with orch.SessionLocal() as session:
        user = orch.ensure_user(session, external_id)
        for m in messages:
            orch._persist_chat_history(session, user_id=user.id, role="user", content=m)
        session.commit()


def _atom_files(root: Path) -> set[Path]:
    return {p.resolve() for p in (root / "atoms").glob("*.md")}


def test_recurrent_pattern_materializes_one_proposed_atom_idempotently(kb_copy: Path, tmp_db_url: str) -> None:
    orch = offline_orchestrator(kb_copy, tmp_db_url)
    try:
        _seed_turns(orch, "wa:+56924444999", DELIVERY[:PATTERN_MIN_COUNT])
        before = _atom_files(kb_copy)
        first = orch.run_reflector()
    finally:
        orch.close()

    # segunda corrida (nuevo proceso): checkpoint en memoria nuevo, pero el atom ya cubre el patron
    again = offline_orchestrator(kb_copy, tmp_db_url)
    try:
        second = again.run_reflector()
    finally:
        again.close()

    new_files = sorted(_atom_files(kb_copy) - before)
    assert len(first) == 1 and second == [] and len(new_files) == 1
    assert first[0]["count"] == PATTERN_MIN_COUNT
    content = Path(first[0]["path"]).read_text(encoding="utf-8")
    assert "- source:reflector" in content and "status: proposed" in content
    assert Path(first[0]["path"]).resolve() == new_files[0]


def test_below_threshold_generates_nothing(kb_copy: Path, tmp_db_url: str) -> None:
    orch = offline_orchestrator(kb_copy, tmp_db_url)
    try:
        _seed_turns(orch, "wa:+56924444004", DELIVERY[: PATTERN_MIN_COUNT - 1])
        before = _atom_files(kb_copy)
        assert orch.run_reflector() == []
        assert _atom_files(kb_copy) == before
    finally:
        orch.close()
