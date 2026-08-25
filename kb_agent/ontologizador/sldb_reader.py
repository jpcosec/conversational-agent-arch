from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KB_ROOT = Path(os.environ.get("KB_ROOT", ".")).resolve()
STORE_NAME = os.environ.get("SLDB_STORE", ".sldb")
SUPPORTED_ATOM_TYPES = frozenset({"rule", "tool", "domain", "trait"})

_TYPE_TAGS: dict[str, tuple[str, ...]] = {
    "rule": ("atom_type:rule", "type:rule", "kb:rule", "topic:rules"),
    "tool": ("atom_type:tool", "type:tool", "kb:tool", "topic:tool-calling"),
    "domain": ("atom_type:domain", "type:domain", "kb:domain", "topic:ontology"),
    "trait": ("atom_type:trait", "type:trait", "kb:trait", "topic:profiling"),
}

_TYPE_TOKENS: dict[str, tuple[str, ...]] = {
    "rule": ("rule", "regla"),
    "tool": ("tool", "api", "function"),
    "domain": ("domain", "dominio"),
    "trait": ("trait", "perfil"),
}


@dataclass(slots=True)
class Atom:
    id: str
    type: str
    tags: list[str]
    body: str


@dataclass(slots=True)
class ToolAtom(Atom):
    json_schema: Any


class SLDBReader:
    def __init__(self, kb_root: Path | str | None = None, store_name: str = STORE_NAME) -> None:
        self.kb_root = Path(kb_root or KB_ROOT).resolve()
        self.store_name = store_name

    @property
    def store_path(self) -> Path:
        return self.kb_root / self.store_name

    def fetch(self, atom_type: str, filters: dict[str, Any] | None = None) -> list[Atom]:
        normalized_type = atom_type.strip().lower()
        if normalized_type not in SUPPORTED_ATOM_TYPES:
            raise ValueError(
                f"Unsupported atom_type '{atom_type}'. Expected one of {sorted(SUPPORTED_ATOM_TYPES)}."
            )

        atoms: list[Atom] = []
        for doc in self._list_documents():
            payload = self._show_document(doc["name"])
            candidate_type = self._infer_atom_type(
                doc_name=doc["name"],
                doc_path=doc.get("path", ""),
                payload=payload,
            )
            if candidate_type != normalized_type:
                continue
            atom = self._build_atom(candidate_type, payload)
            if self._matches_filters(atom=atom, payload=payload, filters=filters):
                atoms.append(atom)
        return atoms

    def _run_sldb(self, *args: str) -> dict[str, Any]:
        proc = subprocess.run(
            ["sldb", *args, "--store", str(self.store_path)],
            cwd=str(self.kb_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "sldb command failed")
        return json.loads(proc.stdout)

    def _list_documents(self) -> list[dict[str, Any]]:
        payload = self._run_sldb("docs", "list", "--format", "json")
        documents = payload.get("documents", [])
        return [doc for doc in documents if doc.get("model") == "AtomDoc"]

    def _show_document(self, name: str) -> dict[str, Any]:
        payload = self._run_sldb("docs", "show", name, "--format", "json")
        return payload["document"]

    def _infer_atom_type(self, doc_name: str, doc_path: str, payload: dict[str, Any]) -> str | None:
        tags = {tag.lower() for tag in payload.get("payload", {}).get("tags", [])}
        title = str(payload.get("payload", {}).get("title") or "").lower()
        identifier = str(payload.get("payload", {}).get("id") or doc_name).lower()
        path = str(doc_path).lower()

        for atom_type, atom_tags in _TYPE_TAGS.items():
            if any(tag in tags for tag in atom_tags):
                return atom_type

        for atom_type, tokens in _TYPE_TOKENS.items():
            corpus = " ".join((identifier, title, path))
            if any(token in corpus for token in tokens):
                return atom_type
        return None

    def _build_atom(self, atom_type: str, payload: dict[str, Any]) -> Atom:
        doc_payload = payload.get("payload", {})
        body = str(doc_payload.get("answer") or "")
        base_kwargs = {
            "id": str(doc_payload.get("id") or payload.get("name") or ""),
            "type": atom_type,
            "tags": list(doc_payload.get("tags") or []),
            "body": body,
        }
        if atom_type == "tool":
            return ToolAtom(json_schema=_extract_json_schema(body), **base_kwargs)
        return Atom(**base_kwargs)

    def _matches_filters(
        self,
        atom: Atom,
        payload: dict[str, Any],
        filters: dict[str, Any] | None,
    ) -> bool:
        if not filters:
            return True

        doc_payload = payload.get("payload", {})
        candidate: dict[str, Any] = {
            "id": atom.id,
            "type": atom.type,
            "tags": atom.tags,
            "body": atom.body,
            "title": doc_payload.get("title"),
            "question": doc_payload.get("five_wh_one_plus"),
            "path": payload.get("path"),
        }
        if isinstance(atom, ToolAtom):
            candidate["json_schema"] = atom.json_schema

        for key, expected in filters.items():
            if key not in candidate:
                return False
            value = candidate[key]
            if key == "tags":
                expected_tags = expected if isinstance(expected, (list, tuple, set)) else [expected]
                if not all(tag in value for tag in expected_tags):
                    return False
                continue
            if isinstance(value, str) and isinstance(expected, str):
                if expected not in value:
                    return False
                continue
            if value != expected:
                return False
        return True


def _extract_json_schema(body: str) -> Any:
    text = body.strip()
    if not text:
        return None

    fenced = _extract_fenced_json(text)
    if fenced is not None:
        return fenced

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def _extract_fenced_json(text: str) -> Any:
    if "```" not in text:
        return None

    chunks = text.split("```")
    for chunk in chunks[1::2]:
        candidate = chunk.strip()
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def fetch(atom_type: str, filters: dict[str, Any] | None = None) -> list[Atom]:
    return SLDBReader().fetch(atom_type=atom_type, filters=filters)
