"""Ingestion declarativa de traits desde el formulario/registro (source='form').

A diferencia del perfilador (que INFIERE rasgos del turno con un LLM), el
formulario de registro DECLARA datos duros: pais, rango etario, para quien
busca, tipo de persona, segmento y proyecto de interes. Esos datos entran
directo a ``user_traits`` con ``source='form'`` y ``confidence=1.0`` -- sin
LLM, sin ambiguedad.

Esta es la puerta de ingestion. La ENTRADA real (payload de n8n/WhatsApp o
del form web) se define aparte; aca solo mapeamos un dict de campos ya
normalizados a ``trait_ids`` de la KB Vitali y los persistimos.

Mapa de campos -> trait_ids
---------------------------
Los ``trait_ids`` referenciados existen como TraitAtoms en
``knowledge_vitali/atoms/`` (categoria ``demographic`` salvo segmento, que es
``behavior``, y proyecto, que es ``preference``). Si un valor no esta en el
mapa se ignora en silencio (un form puede traer campos que aun no modelamos
como trait). El unico requisito duro es no inventar trait_ids.
"""
from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from kb_agent.perfilador.traits_store import SOURCE_FORM, upsert_user_trait

#: Confianza de un dato declarado: maxima, no hay inferencia.
FORM_CONFIDENCE = 1.0

#: Rango etario -> trait_id. Se espera el campo ya bucketizado; si llega una
#: edad numerica cruda se resuelve con ``_age_bucket``.
_AGE_TRAIT = {
    "menos_45": "trait-vitali-edad-menos-45",
    "45_59": "trait-vitali-edad-45-59",
    "60_69": "trait-vitali-edad-60-69",
    "70_mas": "trait-vitali-edad-70-mas",
}

#: Pais (ISO-ish / nombre normalizado) -> trait_id.
_COUNTRY_TRAIT = {
    "chile": "trait-vitali-pais-chile",
    "cl": "trait-vitali-pais-chile",
    "usa": "trait-vitali-pais-usa",
    "us": "trait-vitali-pais-usa",
    "estados_unidos": "trait-vitali-pais-usa",
    "mexico": "trait-vitali-pais-mexico",
    "mx": "trait-vitali-pais-mexico",
    "colombia": "trait-vitali-pais-colombia",
    "co": "trait-vitali-pais-colombia",
    "bolivia": "trait-vitali-pais-bolivia",
    "bo": "trait-vitali-pais-bolivia",
}

#: Para quien busca -> trait_id.
_FOR_WHOM_TRAIT = {
    "mi": "trait-vitali-para-mi",
    "para_mi": "trait-vitali-para-mi",
    "familiar": "trait-vitali-para-familiar",
    "para_familiar": "trait-vitali-para-familiar",
    "inversion": "trait-vitali-para-inversion",
    "para_inversion": "trait-vitali-para-inversion",
}

#: Tipo de persona -> trait_id. Solo "juridica" tiene trait; "natural" es el
#: default implicito y no siembra nada.
_PERSON_TRAIT = {
    "juridica": "trait-vitali-persona-juridica",
    "empresa": "trait-vitali-persona-juridica",
}

#: Segmento de lead -> trait_id.
_SEGMENT_TRAIT = {
    "suite": "trait-vitali-segmento-suite",
    "broker": "trait-vitali-segmento-broker",
    "franquicia": "trait-vitali-segmento-franquicia",
}


def _norm(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _age_bucket(value: object) -> str | None:
    """Convierte una edad numerica cruda en la clave de ``_AGE_TRAIT``."""
    try:
        age = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if age < 45:
        return "menos_45"
    if age < 60:
        return "45_59"
    if age < 70:
        return "60_69"
    return "70_mas"


def map_form_to_trait_ids(form: Mapping[str, object]) -> list[str]:
    """Traduce un dict de campos del form a una lista de ``trait_ids`` (unicos,
    en orden estable). Valores fuera de los mapas se ignoran; ``edad`` acepta
    tanto bucket (``"60_69"``) como edad numerica (``67``)."""
    trait_ids: list[str] = []

    def add(trait_id: str | None) -> None:
        if trait_id and trait_id not in trait_ids:
            trait_ids.append(trait_id)

    if (pais := form.get("pais")) is not None:
        add(_COUNTRY_TRAIT.get(_norm(pais)))

    if (edad := form.get("edad")) is not None:
        key = _norm(edad)
        if key not in _AGE_TRAIT:
            key = _age_bucket(edad) or ""
        add(_AGE_TRAIT.get(key))

    if (para := form.get("para_quien")) is not None:
        add(_FOR_WHOM_TRAIT.get(_norm(para)))

    if (persona := form.get("tipo_persona")) is not None:
        add(_PERSON_TRAIT.get(_norm(persona)))

    if (segmento := form.get("segmento")) is not None:
        add(_SEGMENT_TRAIT.get(_norm(segmento)))

    if form.get("proyecto_interes"):
        add("trait-vitali-proyecto-interes")

    return trait_ids


def ingest_form_traits(
    session: Session,
    *,
    user_id: int,
    form: Mapping[str, object],
    commit: bool = True,
) -> list[str]:
    """Persiste los traits declarados en el form con ``source='form'`` y
    ``confidence=1.0``. Devuelve los ``trait_ids`` escritos.

    No usa LLM. Idempotente y compatible con el perfilador: ``upsert_user_trait``
    resuelve la precedencia de fuente (``form`` gana sobre ``perfilador``).
    """
    trait_ids = map_form_to_trait_ids(form)
    for trait_id in trait_ids:
        upsert_user_trait(
            session,
            user_id=user_id,
            trait_id=trait_id,
            confidence=FORM_CONFIDENCE,
            source=SOURCE_FORM,
        )
    if commit and trait_ids:
        session.commit()
    return trait_ids
