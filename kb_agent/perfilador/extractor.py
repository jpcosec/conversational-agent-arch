from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Protocol

from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import UserTraits
from kb_agent.ontologizador.sldb_reader import SLDBReader

TRAIT_MIN_CONFIDENCE = 0.7
PROFILER_SOURCE = "perfilador"


@dataclass(frozen=True, slots=True)
class TraitCandidate:
    id: str
    body: str


@dataclass(frozen=True, slots=True)
class TraitMatch:
    trait_id: str
    confidence: float


class StructuredTraitMapper(Protocol):
    def extract_traits(
        self,
        *,
        turn_text: str,
        candidates: Sequence[TraitCandidate],
        instructions: str,
    ) -> Sequence[TraitMatch | Mapping[str, Any]]:
        """Return structured trait matches using only the provided candidate ids."""


@dataclass(slots=True)
class TraitExtractor:
    reader: SLDBReader
    identity_session: Session
    llm_mapper: StructuredTraitMapper

    def extract(self, *, user_id: int | None, turn_text: str) -> list[TraitMatch]:
        if user_id is None:
            return []

        cleaned_turn = turn_text.strip()
        if not cleaned_turn:
            return []

        candidates = self._load_candidates()
        if not candidates:
            return []

        raw_matches = self.llm_mapper.extract_traits(
            turn_text=cleaned_turn,
            candidates=candidates,
            instructions=build_trait_mapping_instructions(cleaned_turn, candidates),
        )
        matches = _normalize_matches(raw_matches, candidates)
        if not matches:
            return []

        for match in matches:
            self._upsert_trait(user_id=user_id, match=match)

        self.identity_session.commit()
        return matches

    def _load_candidates(self) -> list[TraitCandidate]:
        return [
            TraitCandidate(id=atom.id, body=atom.body)
            for atom in self.reader.fetch("trait")
        ]

    def _upsert_trait(self, *, user_id: int, match: TraitMatch) -> None:
        persisted = self.identity_session.get(
            UserTraits,
            {"user_id": user_id, "trait_id": match.trait_id},
        )
        if persisted is None:
            self.identity_session.add(
                UserTraits(
                    user_id=user_id,
                    trait_id=match.trait_id,
                    confidence=match.confidence,
                    source=PROFILER_SOURCE,
                )
            )
            return

        persisted.confidence = max(persisted.confidence, match.confidence)
        persisted.source = PROFILER_SOURCE


def extract_traits(
    *,
    user_id: int | None,
    turn_text: str,
    identity_session: Session,
    llm_mapper: StructuredTraitMapper,
    reader: SLDBReader | None = None,
) -> list[TraitMatch]:
    extractor = TraitExtractor(
        reader=reader or SLDBReader(),
        identity_session=identity_session,
        llm_mapper=llm_mapper,
    )
    return extractor.extract(user_id=user_id, turn_text=turn_text)


def build_trait_mapping_instructions(turn_text: str, candidates: Sequence[TraitCandidate]) -> str:
    candidate_lines = "\n".join(f"- {candidate.id}: {candidate.body}" for candidate in candidates)
    return dedent(
        f"""
        Analiza SOLO rasgos EXPLÍCITOS del texto ya scrubbeado.
        No infieras PII, datos sensibles ni rasgos implícitos.
        Elige SOLO trait_ids de la lista de candidatos.
        Si no hay match explícito, devuelve una lista vacía.
        Cada confidence debe estar entre 0 y 1.
        Responde con una lista JSON de objetos con shape exacto:
        [{{"trait_id": "candidate-id", "confidence": 0.91}}]

        Texto del turno:
        {turn_text}

        TraitAtoms candidatos:
        {candidate_lines}
        """
    ).strip()


def _normalize_matches(
    raw_matches: Sequence[TraitMatch | Mapping[str, Any]],
    candidates: Sequence[TraitCandidate],
) -> list[TraitMatch]:
    allowed_ids = {candidate.id for candidate in candidates}
    best_by_trait: dict[str, float] = {}

    for raw_match in raw_matches:
        if isinstance(raw_match, TraitMatch):
            trait_id = raw_match.trait_id
            confidence = raw_match.confidence
        elif isinstance(raw_match, Mapping):
            trait_id = str(raw_match.get("trait_id") or "").strip()
            try:
                confidence = float(raw_match.get("confidence"))
            except (TypeError, ValueError):
                continue
        else:
            continue

        if trait_id not in allowed_ids:
            continue
        if not 0 <= confidence <= 1:
            continue
        if confidence < TRAIT_MIN_CONFIDENCE:
            continue

        current = best_by_trait.get(trait_id)
        if current is None or confidence > current:
            best_by_trait[trait_id] = confidence

    return [
        TraitMatch(trait_id=trait_id, confidence=best_by_trait[trait_id])
        for trait_id in sorted(best_by_trait)
    ]
