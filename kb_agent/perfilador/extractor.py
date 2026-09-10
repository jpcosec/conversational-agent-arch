from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy.orm import Session

from kb_agent.perfilador.traits_store import SOURCE_PROFILER, upsert_user_trait

if TYPE_CHECKING:
    from knowledge_base.operations import KnowledgeOperations

TRAIT_MIN_CONFIDENCE = 0.7
#: Reexport por compatibilidad; la fuente canonica vive en ``traits_store``.
PROFILER_SOURCE = SOURCE_PROFILER

#: Top-k de traits candidatos que se pasan al LLM tras el pre-filtro semantico.
#: Con la KB creciendo, evita inflar el prompt de extraccion cada turno.
DEFAULT_TRAIT_TOPK = 10
#: Piso de ruido de embedding (mismo default que KnowledgeOperations). No es un
#: corte de relevancia, solo descarta similitud puramente ruidosa.
DEFAULT_TRAIT_NOISE_FLOOR = 0.05


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
    knowledge: "KnowledgeOperations"
    #: Sesion SQL de identidad. Solo la usan ``persist``/``extract``;
    #: ``analyze`` (embedder + LLM) no toca la base, por eso es opcional:
    #: el hilo del perfilador construye el extractor sin sesion.
    identity_session: Session | None = None
    llm_mapper: StructuredTraitMapper | None = None
    #: Instancia unica de KnowledgeOperations del proceso (embedder cacheado).
    #: Si es None (tests unitarios, o KB sin embeddings) el ranking cae al
    #: comportamiento previo: pasar TODOS los candidatos.
    knowledge_ops: "KnowledgeOperations | None" = None
    top_k: int = DEFAULT_TRAIT_TOPK
    noise_floor: float = DEFAULT_TRAIT_NOISE_FLOOR

    def analyze(self, *, user_id: int | None, turn_text: str) -> list[TraitMatch]:
        """Traits que el turno revela, SIN tocar la base de identidad.

        Es la parte cara (embedder + LLM) y la unica que vale la pena correr
        en paralelo con el turno. La escritura queda aparte (``persist``)
        para que la haga el hilo dueno de la sesion SQL: dos hilos escribiendo
        la misma conexion sqlite se pisan ("cannot commit transaction - SQL
        statements in progress", medido en la suite).
        """
        if user_id is None:
            return []

        cleaned_turn = turn_text.strip()
        if not cleaned_turn:
            return []

        candidates = self._load_candidates()
        if not candidates:
            return []

        candidates = self._rank_candidates(cleaned_turn, candidates)

        raw_matches = self.llm_mapper.extract_traits(
            turn_text=cleaned_turn,
            candidates=candidates,
            instructions=build_trait_mapping_instructions(cleaned_turn, candidates),
        )
        return _normalize_matches(raw_matches, candidates)

    def persist(self, *, user_id: int | None, matches: Sequence[TraitMatch]) -> list[TraitMatch]:
        """Escribe en ``user_traits`` los matches de ``analyze``."""
        if user_id is None or not matches:
            return []
        for match in matches:
            self._upsert_trait(user_id=user_id, match=match)
        self.identity_session.commit()
        return list(matches)

    def extract(self, *, user_id: int | None, turn_text: str) -> list[TraitMatch]:
        """analyze + persist en un paso (llamadores que ya tienen la sesion)."""
        return self.persist(user_id=user_id, matches=self.analyze(user_id=user_id, turn_text=turn_text))

    def _load_candidates(self) -> list[TraitCandidate]:
        """Carga los trait atoms desde la KB (dict o objeto)."""
        result = []
        for t in self.knowledge.docs_by_type("trait"):
            if isinstance(t, dict):
                # TraitAtom tipado usa ``description``; fallback a ``answer``.
                result.append(TraitCandidate(id=t["id"], body=t.get("description") or t.get("answer", "")))
            else:
                result.append(TraitCandidate(id=t.id, body=getattr(t, "body", "")))
        return result

    def _rank_candidates(
        self, turn_text: str, candidates: list[TraitCandidate]
    ) -> list[TraitCandidate]:
        """Pre-filtra los candidatos por similitud turno-vs-trait y deja top-k,
        en vez de mandar TODOS los traits al LLM cada turno.

        La similitud la da el indice de documentos de la KB
        (``KnowledgeOperations.rank_among`` -> ``pron.DocumentIndex``), el
        mismo que usa el compilador. Fail-open: sin knowledge_ops, con un
        catalogo que ya cabe en el top-k, o si el indice falla, devuelve
        TODOS los candidatos. Un trait sin vector en el indice no compite:
        se anexa siempre fuera del ranking.
        """
        if self.knowledge_ops is None or len(candidates) <= self.top_k:
            return candidates
        by_id = {c.id: c for c in candidates}
        try:
            ranked = self.knowledge_ops.rank_among(
                turn_text, list(by_id), k=self.top_k, threshold=self.noise_floor,
            )
        except Exception:
            return candidates
        indexed = set(self.knowledge_ops.document_index().keys())
        top = [by_id[cid] for cid, _ in ranked if cid in by_id]
        unindexed = [c for c in candidates if c.id not in indexed and c not in top]
        return top + unindexed

    def _upsert_trait(self, *, user_id: int, match: TraitMatch) -> None:
        upsert_user_trait(
            self.identity_session,
            user_id=user_id,
            trait_id=match.trait_id,
            confidence=match.confidence,
            source=SOURCE_PROFILER,
        )


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
