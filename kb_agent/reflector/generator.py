from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from deskops.atom_tags import default_registry_path, validate_atom_tag_namespaces

from knowledge_base.operations import KnowledgeOperations
from kb_agent.reflector.reader import ReflectorHistoryRow

PATTERN_MIN_COUNT = 5
SOURCE_TAG = "source:reflector"


@dataclass(frozen=True, slots=True)
class RecurrentPattern:
    normalized_text: str
    canonical_text: str
    count: int
    atom_type: str


@dataclass(frozen=True, slots=True)
class GeneratedAtom:
    atom_id: str
    atom_type: str
    path: Path
    normalized_text: str
    count: int


class ReflectorAtomGenerator:
    """Propone atoms de la KB (``DomainAtom``/``RuleAtom``) a partir de patrones
    recurrentes del historial. Escribe por ``KnowledgeOperations.propose`` (una
    escritura de sldb por libreria, trackeada, con tags ``status:proposed`` y
    ``source:reflector``); ``promote`` los activa despues.
    """

    def __init__(
        self,
        *,
        kb_root: Path | str,
        pattern_min_count: int = PATTERN_MIN_COUNT,
        pythonpath: Path | str | None = None,
        knowledge: KnowledgeOperations | None = None,
        registry_root: Path | str | None = None,
    ) -> None:
        if pattern_min_count <= 0:
            raise ValueError("pattern_min_count must be greater than zero")
        self.kb_root = Path(kb_root).resolve()
        self.pattern_min_count = pattern_min_count
        self.pythonpath = str(Path(pythonpath or self.kb_root.parent).resolve())
        #: donde vive ``desk/atoms/tag-namespaces.yaml`` (el registro de namespaces
        #: que gobierna los tags que el Reflector puede escribir).
        self.registry_root = Path(registry_root or self.kb_root).resolve()
        self._knowledge = knowledge or KnowledgeOperations(kb_root=self.kb_root, pythonpath=self.pythonpath)

    def generate(self, rows: Iterable[ReflectorHistoryRow]) -> list[GeneratedAtom]:
        self._validate_required_namespaces()
        patterns = self._detect_patterns(rows)
        if not patterns:
            return []
        covered = self._existing_normalized_texts()
        generated: list[GeneratedAtom] = []
        for pattern in patterns:
            if pattern.normalized_text in covered:
                continue
            generated.append(self._create_atom(pattern))
            covered.add(pattern.normalized_text)
        return generated

    def _detect_patterns(self, rows: Iterable[ReflectorHistoryRow]) -> list[RecurrentPattern]:
        grouped: dict[str, list[ReflectorHistoryRow]] = defaultdict(list)
        for row in rows:
            if row.role.strip().lower() != "user":
                continue
            normalized = normalize_text(row.content)
            if not normalized:
                continue
            grouped[normalized].append(row)

        recurrent: list[RecurrentPattern] = []
        for normalized, matches in grouped.items():
            distinct_turns = {row.id for row in matches}
            if len(distinct_turns) < self.pattern_min_count:
                continue
            ordered = sorted(matches, key=lambda row: (row.created_at, row.id))
            canonical = ordered[0].content.strip()
            recurrent.append(
                RecurrentPattern(
                    normalized_text=normalized,
                    canonical_text=canonical,
                    count=len(distinct_turns),
                    atom_type=_infer_atom_type(normalized),
                )
            )

        recurrent.sort(key=lambda item: (-item.count, item.normalized_text))
        return recurrent

    def _existing_normalized_texts(self) -> set[str]:
        """Lo que la KB ya cubre (activo o propuesto): answer, id y title de cada
        DomainAtom/RuleAtom, normalizados."""
        normalized: set[str] = set()
        for atom_type in ("domain", "rule"):
            for atom in self._knowledge.docs_by_type(atom_type):
                for text in (atom.get("answer", ""), atom.get("id", ""), atom.get("title", "")):
                    normalized.add(normalize_text(str(text or "")))
        return {value for value in normalized if value}

    def _create_atom(self, pattern: RecurrentPattern) -> GeneratedAtom:
        payload = self._payload_for_pattern(pattern)
        created = self._knowledge.propose(pattern.atom_type, payload)
        return GeneratedAtom(
            atom_id=created["id"],
            atom_type=pattern.atom_type,
            path=Path(created["path"]),
            normalized_text=pattern.normalized_text,
            count=pattern.count,
        )

    def _payload_for_pattern(self, pattern: RecurrentPattern) -> dict[str, object]:
        atom_label = "Rule" if pattern.atom_type == "rule" else "Domain"
        title = f"{atom_label}: {pattern.canonical_text.strip()}"
        tags = [SOURCE_TAG, _topic_tag_for_type(pattern.atom_type)]
        validate_atom_tag_namespaces(tags, default_registry_path(self.registry_root))
        answer = pattern.canonical_text.strip()
        summary = answer if len(answer) <= 160 else answer[:157].rstrip() + "..."
        return {
            "id": f"atom-{_slugify(title)}",
            "title": title,
            "five_wh_one_plus": "what",
            "answer": answer,
            "summary": summary,
            "tags": tags,
            "provenance": "kb_agent/reflector/generator.py",
        }

    def _validate_required_namespaces(self) -> None:
        validate_atom_tag_namespaces([SOURCE_TAG], default_registry_path(self.registry_root))


def normalize_text(text: str) -> str:
    lowered = text.strip().lower()
    if not lowered:
        return ""
    without_punctuation = "".join(
        ch if not unicodedata.category(ch).startswith("P") else " "
        for ch in lowered
    )
    return " ".join(without_punctuation.split())


def _infer_atom_type(normalized_text: str) -> str:
    rule_markers = ("si ", "debe ", "deben ", "prohibido ", "nunca ", "siempre ")
    return "rule" if normalized_text.startswith(rule_markers) else "domain"


def _topic_tag_for_type(atom_type: str) -> str:
    return "topic:rules" if atom_type == "rule" else "topic:ontology"


def _slugify(text: str) -> str:
    normalized = normalize_text(text)
    slug = normalized.replace(" ", "-")
    return slug or "reflector-pattern"
