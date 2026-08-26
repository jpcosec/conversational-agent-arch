from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml
from deskops.atom_tags import default_registry_path, validate_atom_tag_namespaces

from kb_agent.ontologizador.sldb_reader import SLDBReader
from kb_agent.reflector.reader import ReflectorHistoryRow

PATTERN_MIN_COUNT = 5
PROPOSED_STATUS = "proposed"
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
    def __init__(
        self,
        *,
        kb_root: Path | str | None = None,
        store_name: str = ".sldb",
        output_dir: Path | str | None = None,
        pattern_min_count: int = PATTERN_MIN_COUNT,
        pythonpath: Path | str | None = None,
    ) -> None:
        if pattern_min_count <= 0:
            raise ValueError("pattern_min_count must be greater than zero")

        self.kb_root = Path(kb_root or ".").resolve()
        self.store_name = store_name
        self.store_path = self.kb_root / store_name
        self.output_dir = Path(output_dir or (self.kb_root / "desk" / "atoms")).resolve()
        self.pattern_min_count = pattern_min_count
        self.pythonpath = str(Path(pythonpath or self.kb_root).resolve())
        self._reader = SLDBReader(kb_root=self.kb_root, store_name=store_name)

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
            created = self._create_atom(pattern)
            generated.append(created)
            covered.add(pattern.normalized_text)

        if generated:
            self._run_sldb("stores", "update")

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
        normalized: set[str] = set()
        seen_docs: set[str] = set()

        for atom_type in ("domain", "rule"):
            for atom in self._reader.fetch(atom_type):
                atom_id = atom["id"] if isinstance(atom, dict) else atom.id
                atom_body = atom.get("answer", "") if isinstance(atom, dict) else atom.body
                seen_docs.add(atom_id)
                if atom_body:
                    normalized.add(normalize_text(atom_body))
                normalized.add(normalize_text(atom_id))

        docs_payload = json.loads(self._run_sldb("docs", "list", "--format", "json"))
        for doc in docs_payload.get("documents", []):
            if doc.get("model") != "AtomDoc":
                continue
            name = str(doc.get("name") or "")
            if name and name not in seen_docs:
                payload = json.loads(self._run_sldb("docs", "show", name, "--format", "json"))
                doc_payload = payload.get("document", {}).get("payload", {})
                tags = {str(tag).lower() for tag in doc_payload.get("tags", [])}
                if "topic:ontology" not in tags and "topic:rules" not in tags:
                    continue
                normalized.add(normalize_text(str(doc_payload.get("title") or "")))
                normalized.add(normalize_text(str(doc_payload.get("answer") or "")))

        return {value for value in normalized if value}

    def _create_atom(self, pattern: RecurrentPattern) -> GeneratedAtom:
        payload = self._payload_for_pattern(pattern)
        atom_id = str(payload["id"])
        output_path = self.output_dir / f"{atom_id}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
            payload_path = Path(handle.name)

        try:
            self._run_sldb(
                "docs",
                "create",
                "--model",
                "AtomDoc",
                "-o",
                str(output_path),
                str(payload_path),
            )
        finally:
            payload_path.unlink(missing_ok=True)

        self._inject_status(output_path, PROPOSED_STATUS)
        return GeneratedAtom(
            atom_id=atom_id,
            atom_type=pattern.atom_type,
            path=output_path,
            normalized_text=pattern.normalized_text,
            count=pattern.count,
        )

    def _payload_for_pattern(self, pattern: RecurrentPattern) -> dict[str, object]:
        atom_label = "Rule" if pattern.atom_type == "rule" else "Domain"
        title = f"{atom_label}: {pattern.canonical_text.strip()}"
        tags = [SOURCE_TAG, _topic_tag_for_type(pattern.atom_type)]
        validate_atom_tag_namespaces(tags, default_registry_path(self.kb_root))
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

    def _inject_status(self, path: Path, status: str) -> None:
        text = path.read_text(encoding="utf-8")
        if "\nstatus:" in text.split("---", 2)[1]:
            return
        frontmatter_end = text.find("\n---\n", 4)
        if frontmatter_end == -1:
            raise ValueError(f"Could not locate frontmatter boundary in {path}")
        updated = f"{text[:frontmatter_end]}\nstatus: {status}{text[frontmatter_end:]}"
        path.write_text(updated, encoding="utf-8")

    def _validate_required_namespaces(self) -> None:
        validate_atom_tag_namespaces([SOURCE_TAG], default_registry_path(self.kb_root))

    def _run_sldb(self, *args: str) -> str:
        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = self.pythonpath if not current_pythonpath else f"{self.pythonpath}{os.pathsep}{current_pythonpath}"
        proc = subprocess.run(
            ["sldb", *args, "--store", str(self.store_path)],
            cwd=str(self.kb_root),
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "sldb command failed")
        return proc.stdout


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
