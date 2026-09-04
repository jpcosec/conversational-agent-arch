"""Perfilador: TraitExtractor (SLDB candidatos -> mapper -> UserTraits en SQL)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from knowledge_base.operations import KnowledgeOperations
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
    return TraitExtractor(knowledge=KnowledgeOperations(kb_root=kb_root), identity_session=session, llm_mapper=mapper)


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


# ── pre-filtro semantico (top-k) ──────────────────────────────────────────


class _FakeEmbedder:
    """Embedder deterministico: mapea textos a vectores fijos por keyword."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def embed(self, texts):
        out = []
        for t in texts:
            key = next((k for k in self._vectors if k in t), None)
            out.append(self._vectors.get(key, [0.0, 0.0, 1.0]))
        return out


class _FakeKnowledgeOps:
    def __init__(self, embedder) -> None:
        self._embedder_obj = embedder

    def _embedder(self):
        return self._embedder_obj


def _cand(cid: str, vec):
    from kb_agent.perfilador.extractor import TraitCandidate

    return TraitCandidate(id=cid, body=cid, embedding=tuple(vec) if vec else None)


def test_rank_candidates_keeps_only_topk_by_similarity(kb_root: Path, session: tuple[Session, int]) -> None:
    s, _ = session
    embedder = _FakeEmbedder({"quiero suite": [1.0, 0.0, 0.0]})
    ops = _FakeKnowledgeOps(embedder)
    extractor = TraitExtractor(
        knowledge=KnowledgeOperations(kb_root=kb_root),
        identity_session=s,
        llm_mapper=ScriptedMapper([]),
        knowledge_ops=ops,
        top_k=1,
    )
    cands = [
        _cand("trait-cerca", [1.0, 0.0, 0.0]),   # coseno 1.0 con la query
        _cand("trait-lejos", [0.0, 1.0, 0.0]),   # coseno 0.0 -> bajo el piso
    ]
    ranked = extractor._rank_candidates("quiero suite", cands)
    assert [c.id for c in ranked] == ["trait-cerca"]


def test_rank_candidates_always_keeps_traits_without_embedding(kb_root: Path, session: tuple[Session, int]) -> None:
    s, _ = session
    embedder = _FakeEmbedder({"hola": [1.0, 0.0, 0.0]})
    ops = _FakeKnowledgeOps(embedder)
    extractor = TraitExtractor(
        knowledge=KnowledgeOperations(kb_root=kb_root),
        identity_session=s,
        llm_mapper=ScriptedMapper([]),
        knowledge_ops=ops,
        top_k=1,
    )
    cands = [
        _cand("trait-emb", [1.0, 0.0, 0.0]),
        _cand("trait-declarativo", None),   # sin embedding -> siempre incluido
    ]
    ranked = extractor._rank_candidates("hola", cands)
    assert set(c.id for c in ranked) == {"trait-emb", "trait-declarativo"}


def test_rank_candidates_falls_back_to_all_without_knowledge_ops(kb_root: Path, session: tuple[Session, int]) -> None:
    s, _ = session
    extractor = _extractor(kb_root, s, ScriptedMapper([]))  # knowledge_ops=None
    cands = [_cand("a", [1.0, 0.0, 0.0]), _cand("b", [0.0, 1.0, 0.0])]
    assert extractor._rank_candidates("x", cands) == cands
