"""Perfilador: TraitExtractor (SLDB candidatos -> mapper -> UserTraits en SQL)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.ontologizador.sldb_reader import SLDBReader
from kb_agent.perfilador.extractor import PROFILER_SOURCE, TRAIT_MIN_CONFIDENCE, TraitExtractor, TraitMatch
from tests.support.sldb_seed import seed_store


class ScriptedMapper:
    def __init__(self, responses: list[list]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def extract_traits(self, *, turn_text, candidates, instructions):
        self.calls.append({"turn_text": turn_text, "candidates": list(candidates), "instructions": instructions})
        return self._responses.pop(0)


@pytest.fixture(scope="module")
def kb_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return seed_store(
        tmp_path_factory.mktemp("kb") / "traits",
        [{"type": "trait", "id": "trait-vegetariano", "title": "Trait Vegetariano", "tags": ["user:traits.vegetariano"], "category": "dietary", "fields": {"description": "soy vegetariano"}}],
    )


@pytest.fixture()
def session() -> tuple[Session, int]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = Session(engine)
    user = Users(external_id="wa:+56912345678", channel="whatsapp")
    s.add(user)
    s.commit()
    try:
        yield s, user.id
    finally:
        s.close()


def _extractor(kb_root: Path, session: Session, mapper) -> TraitExtractor:
    return TraitExtractor(reader=SLDBReader(kb_root=kb_root), identity_session=session, llm_mapper=mapper)


def test_explicit_signal_creates_user_trait_row(kb_root: Path, session: tuple[Session, int]) -> None:
    s, user_id = session
    mapper = ScriptedMapper([[TraitMatch(trait_id="trait-vegetariano", confidence=0.93)]])
    matches = _extractor(kb_root, s, mapper).extract(user_id=user_id, turn_text="soy vegetariano")

    assert matches == [TraitMatch(trait_id="trait-vegetariano", confidence=0.93)]
    row = s.scalar(select(UserTraits).where(UserTraits.user_id == user_id))
    assert (row.trait_id, row.confidence, row.source) == ("trait-vegetariano", 0.93, PROFILER_SOURCE)
    # el mapper recibe el catalogo tipado (TraitAtom.description) y las instrucciones
    assert [c.id for c in mapper.calls[0]["candidates"]] == ["trait-vegetariano"]
    assert mapper.calls[0]["candidates"][0].body == "soy vegetariano"
    assert "trait-vegetariano" in mapper.calls[0]["instructions"]


def test_unknown_or_low_confidence_matches_are_dropped(kb_root: Path, session: tuple[Session, int]) -> None:
    s, user_id = session
    mapper = ScriptedMapper([[
        {"trait_id": "trait-celiaco", "confidence": 0.99},                      # no esta en el catalogo
        {"trait_id": "trait-vegetariano", "confidence": TRAIT_MIN_CONFIDENCE - 0.01},  # bajo umbral
        {"trait_id": "trait-vegetariano", "confidence": "no-numero"},           # basura
    ]])
    assert _extractor(kb_root, s, mapper).extract(user_id=user_id, turn_text="soy celiaco") == []
    assert s.scalars(select(UserTraits)).all() == []


def test_reprocessing_is_idempotent_and_keeps_max_confidence(kb_root: Path, session: tuple[Session, int]) -> None:
    s, user_id = session
    mapper = ScriptedMapper([
        [{"trait_id": "trait-vegetariano", "confidence": 0.72}],
        [{"trait_id": "trait-vegetariano", "confidence": 0.88}],
        [{"trait_id": "trait-vegetariano", "confidence": 0.75}],
    ])
    extractor = _extractor(kb_root, s, mapper)
    for _ in range(3):
        extractor.extract(user_id=user_id, turn_text="soy vegetariano")

    rows = s.scalars(select(UserTraits).where(UserTraits.user_id == user_id)).all()
    assert len(rows) == 1
    assert rows[0].confidence == 0.88


def test_skips_llm_when_no_user_or_empty_turn(kb_root: Path, session: tuple[Session, int]) -> None:
    s, user_id = session
    mapper = ScriptedMapper([])
    extractor = _extractor(kb_root, s, mapper)
    assert extractor.extract(user_id=None, turn_text="soy vegetariano") == []
    assert extractor.extract(user_id=user_id, turn_text="   ") == []
    assert mapper.calls == []
