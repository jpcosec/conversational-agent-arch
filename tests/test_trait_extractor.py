from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.ontologizador.sldb_reader import SLDBReader
from kb_agent.perfilador.extractor import PROFILER_SOURCE, TraitCandidate, TraitExtractor, TraitMatch


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeTraitMapper:
    def __init__(self, responses: Sequence[Sequence[TraitMatch | dict[str, Any]]]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def extract_traits(
        self,
        *,
        turn_text: str,
        candidates: Sequence[TraitCandidate],
        instructions: str,
    ) -> Sequence[TraitMatch | dict[str, Any]]:
        self.calls.append(
            {
                "turn_text": turn_text,
                "candidates": list(candidates),
                "instructions": instructions,
            }
        )
        if not self._responses:
            raise AssertionError("No fake LLM responses remaining")
        return self._responses.pop(0)


def test_explicit_trait_signal_creates_user_trait_row(tmp_path: Path) -> None:
    kb_root = _seed_store(
        tmp_path / "kb",
        atoms=[
            {
                "id": "trait-vegetariano",
                "title": "Trait Vegetariano",
                "tags": ["user:traits.vegetariano", "system:donpeppe"],
                "description": "soy vegetariano",
            }
        ],
    )
    session, user_id = _build_identity_session()
    mapper = FakeTraitMapper([
        [TraitMatch(trait_id="trait-vegetariano", confidence=0.93)],
    ])

    try:
        extractor = TraitExtractor(
            reader=SLDBReader(kb_root=kb_root, store_name=".sldb_test"),
            identity_session=session,
            llm_mapper=mapper,
        )

        matches = extractor.extract(user_id=user_id, turn_text="soy vegetariano")

        assert matches == [TraitMatch(trait_id="trait-vegetariano", confidence=0.93)]
        persisted = session.scalar(select(UserTraits).where(UserTraits.user_id == user_id))
        assert persisted is not None
        assert persisted.trait_id == "trait-vegetariano"
        assert persisted.confidence == 0.93
        assert persisted.source == PROFILER_SOURCE
        assert [candidate.id for candidate in mapper.calls[0]["candidates"]] == ["trait-vegetariano"]
        assert mapper.calls[0]["candidates"][0].body == "soy vegetariano"
    finally:
        session.close()


def test_signal_without_matching_trait_atom_does_not_persist_row(tmp_path: Path) -> None:
    kb_root = _seed_store(
        tmp_path / "kb",
        atoms=[
            {
                "id": "trait-vegetariano",
                "title": "Trait Vegetariano",
                "tags": ["user:traits.vegetariano", "system:donpeppe"],
                "description": "soy vegetariano",
            }
        ],
    )
    session, user_id = _build_identity_session()
    mapper = FakeTraitMapper([
        [{"trait_id": "trait-celiaco", "confidence": 0.99}],
    ])

    try:
        extractor = TraitExtractor(
            reader=SLDBReader(kb_root=kb_root, store_name=".sldb_test"),
            identity_session=session,
            llm_mapper=mapper,
        )

        matches = extractor.extract(user_id=user_id, turn_text="soy celiaco")

        assert matches == []
        assert session.scalars(select(UserTraits).where(UserTraits.user_id == user_id)).all() == []
    finally:
        session.close()


def test_reprocessing_same_signal_is_idempotent_and_keeps_max_confidence(tmp_path: Path) -> None:
    kb_root = _seed_store(
        tmp_path / "kb",
        atoms=[
            {
                "id": "trait-vegetariano",
                "title": "Trait Vegetariano",
                "tags": ["user:traits.vegetariano", "system:donpeppe"],
                "description": "soy vegetariano",
            }
        ],
    )
    session, user_id = _build_identity_session()
    mapper = FakeTraitMapper([
        [{"trait_id": "trait-vegetariano", "confidence": 0.72}],
        [{"trait_id": "trait-vegetariano", "confidence": 0.88}],
    ])

    try:
        extractor = TraitExtractor(
            reader=SLDBReader(kb_root=kb_root, store_name=".sldb_test"),
            identity_session=session,
            llm_mapper=mapper,
        )

        first = extractor.extract(user_id=user_id, turn_text="soy vegetariano")
        second = extractor.extract(user_id=user_id, turn_text="soy vegetariano")

        rows = session.scalars(select(UserTraits).where(UserTraits.user_id == user_id)).all()
        assert first == [TraitMatch(trait_id="trait-vegetariano", confidence=0.72)]
        assert second == [TraitMatch(trait_id="trait-vegetariano", confidence=0.88)]
        assert len(rows) == 1
        assert rows[0].trait_id == "trait-vegetariano"
        assert rows[0].confidence == 0.88
        assert rows[0].source == PROFILER_SOURCE
    finally:
        session.close()


def _build_identity_session() -> tuple[Session, int]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = Users(external_id="wa:+56912345678", channel="whatsapp")
    session.add(user)
    session.commit()
    return session, user.id


def _seed_store(root: Path, atoms: list[dict[str, object]]) -> Path:
    """Seed de un TraitAtom tipado (seleccionable por type.knowledge.trait)."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["sldb", "stores", "init", "--path", str(root)])
    store = root / ".sldb"
    _run(
        [
            "sldb", "models", "add", "kb_agent.models.knowledge:TraitAtom",
            "--store", str(store), "--pythonpath", str(REPO_ROOT),
        ]
    )

    for atom in atoms:
        rel_path = Path("atoms") / f"{atom['id']}.md"
        out_path = root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_atom_markdown(atom), encoding="utf-8")
        _run(
            [
                "sldb", "docs", "track", str(rel_path),
                "--model", "TraitAtom",
                "--store", str(store), "--pythonpath", str(REPO_ROOT),
            ]
        )

    _run(["sldb", "stores", "update", "--store", str(store), "--pythonpath", str(REPO_ROOT)])
    os.symlink(store, root / ".sldb_test", target_is_directory=True)
    return root


def _atom_markdown(atom: dict[str, object]) -> str:
    tags = "\n".join(f"- {tag}" for tag in atom["tags"])  # type: ignore[union-attr]
    return (
        "---\n"
        f"id: {atom['id']}\n"
        f"title: {atom['title']}\n"
        "atom_type: trait\n"
        "tags:\n"
        f"{tags}\n"
        "category: dietary\n"
        "provenance: null\n"
        "---\n"
        "\n"
        f"# {atom['title']}\n"
        "\n"
        "## Description\n"
        "\n"
        f"{atom['description']}\n"
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
