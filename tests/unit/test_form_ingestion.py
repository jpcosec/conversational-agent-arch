"""Ingestion declarativa de traits desde el form (source='form', sin LLM)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.perfilador.form_ingestion import (
    FORM_CONFIDENCE,
    ingest_form_traits,
    map_form_to_trait_ids,
)
from kb_agent.perfilador.traits_store import (
    SOURCE_FORM,
    SOURCE_PROFILER,
    upsert_user_trait,
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


def _traits(s: Session, user_id: int) -> dict[str, tuple[float, str]]:
    rows = s.scalars(select(UserTraits).where(UserTraits.user_id == user_id)).all()
    return {r.trait_id: (r.confidence, r.source) for r in rows}


# ── mapeo de campos ────────────────────────────────────────────────────────


def test_maps_all_known_fields_to_trait_ids() -> None:
    form = {
        "pais": "Chile",
        "edad": "60_69",
        "para_quien": "familiar",
        "tipo_persona": "juridica",
        "segmento": "broker",
        "proyecto_interes": "Chicureo",
    }
    assert map_form_to_trait_ids(form) == [
        "trait-vitali-pais-chile",
        "trait-vitali-edad-60-69",
        "trait-vitali-para-familiar",
        "trait-vitali-persona-juridica",
        "trait-vitali-segmento-broker",
        "trait-vitali-proyecto-interes",
    ]


def test_age_accepts_raw_numeric_and_buckets_it() -> None:
    assert map_form_to_trait_ids({"edad": 67}) == ["trait-vitali-edad-60-69"]
    assert map_form_to_trait_ids({"edad": 40}) == ["trait-vitali-edad-menos-45"]
    assert map_form_to_trait_ids({"edad": 72}) == ["trait-vitali-edad-70-mas"]


def test_unknown_values_and_natural_person_are_ignored() -> None:
    assert map_form_to_trait_ids({"pais": "Peru", "tipo_persona": "natural"}) == []
    assert map_form_to_trait_ids({"segmento": "otro"}) == []
    assert map_form_to_trait_ids({}) == []


def test_country_aliases_normalize() -> None:
    assert map_form_to_trait_ids({"pais": "US"}) == ["trait-vitali-pais-usa"]
    assert map_form_to_trait_ids({"pais": "estados unidos"}) == ["trait-vitali-pais-usa"]


# ── persistencia ───────────────────────────────────────────────────────────


def test_ingest_persists_with_form_source_and_full_confidence(
    session: tuple[Session, int]
) -> None:
    s, user_id = session
    written = ingest_form_traits(s, user_id=user_id, form={"pais": "Chile", "edad": 67})
    assert set(written) == {"trait-vitali-pais-chile", "trait-vitali-edad-60-69"}
    persisted = _traits(s, user_id)
    assert persisted["trait-vitali-pais-chile"] == (FORM_CONFIDENCE, SOURCE_FORM)
    assert persisted["trait-vitali-edad-60-69"] == (FORM_CONFIDENCE, SOURCE_FORM)


def test_ingest_is_idempotent(session: tuple[Session, int]) -> None:
    s, user_id = session
    ingest_form_traits(s, user_id=user_id, form={"pais": "Chile"})
    ingest_form_traits(s, user_id=user_id, form={"pais": "Chile"})
    rows = s.scalars(select(UserTraits).where(UserTraits.user_id == user_id)).all()
    assert len(rows) == 1


# ── precedencia de fuente (form > perfilador) ──────────────────────────────


def test_form_overrides_profiler_source_keeping_max_confidence(
    session: tuple[Session, int]
) -> None:
    s, user_id = session
    # el perfilador lo infirio antes con confianza parcial
    upsert_user_trait(
        s, user_id=user_id, trait_id="trait-vitali-pais-chile",
        confidence=0.8, source=SOURCE_PROFILER,
    )
    s.commit()
    # luego la persona lo declara en el form -> form gana el source
    ingest_form_traits(s, user_id=user_id, form={"pais": "Chile"})
    conf, source = _traits(s, user_id)["trait-vitali-pais-chile"]
    assert source == SOURCE_FORM
    assert conf == FORM_CONFIDENCE  # max(0.8, 1.0)


def test_profiler_does_not_downgrade_a_form_trait(
    session: tuple[Session, int]
) -> None:
    s, user_id = session
    ingest_form_traits(s, user_id=user_id, form={"pais": "Chile"})
    # el perfilador vuelve a tocar el mismo trait con menor confianza
    upsert_user_trait(
        s, user_id=user_id, trait_id="trait-vitali-pais-chile",
        confidence=0.6, source=SOURCE_PROFILER,
    )
    s.commit()
    conf, source = _traits(s, user_id)["trait-vitali-pais-chile"]
    assert source == SOURCE_FORM  # no se degrada
    assert conf == FORM_CONFIDENCE
