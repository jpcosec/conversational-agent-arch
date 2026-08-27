from __future__ import annotations

import json
import os
import subprocess
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from deskops.atom_tags import default_registry_path, validate_atom_tag_namespaces

from sldb.cli.model_utils import resolve_model_ref
from sldb.runtime.validation import render_model_markdown, validate_model_input_roundtrip
from sldb.store.io import load_store_index
from sldb.store.layout import project_root as sldb_project_root
from sldb.store.ops import track_document

from kb_agent.ontologizador.sldb_reader import SLDBReader
from kb_agent.reflector.reader import ReflectorHistoryRow

PATTERN_MIN_COUNT = 5
PROPOSED_STATUS = "proposed"
SOURCE_TAG = "source:reflector"
ATOM_MODEL_NAME = "AtomDoc"


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

        model_type, model_entry, store_index = self._resolve_model(ATOM_MODEL_NAME)
        rendered = render_model_markdown(model_type, payload)
        is_valid, details = validate_model_input_roundtrip(model_type, rendered)
        if not is_valid:
            raise ValueError(f"Reflector atom failed roundtrip validation: {details}")

        final_text = self._with_status(rendered, PROPOSED_STATUS)
        output_path.write_text(final_text, encoding="utf-8")
        # OJO: el "project root" del store NO es necesariamente `self.kb_root`.
        # `Orchestrator.run_reflector` llama a este generador con
        # `kb_root=self.repo_root` (para pythonpath) y `store_name=<ruta
        # absoluta al .sldb del KB>`; `self.store_path` termina apuntando
        # bien porque `Path(kb_root) / store_name_absoluto` descarta el lado
        # izquierdo (comportamiento de pathlib con un operando absoluto), pero
        # `self.kb_root` en ese caso queda siendo el repo root, no el
        # directorio que CONTIENE el store. `track_document` necesita el
        # directorio real que contiene `.sldb` (para resolver `doc.path`,
        # relativo a él) -- se deriva del propio `store_path`, no de
        # `self.kb_root`.
        track_document(
            self.store_path, sldb_project_root(self.store_path), store_index, model_type, model_entry,
            output_path, atom_id, resolve_model_ref, self.pythonpath,
        )

        return GeneratedAtom(
            atom_id=atom_id,
            atom_type=pattern.atom_type,
            path=output_path,
            normalized_text=pattern.normalized_text,
            count=pattern.count,
        )

    def _resolve_model(self, model_name: str) -> tuple[type, Any, Any]:
        """Resuelve (model_type, model_entry, store_index) para un modelo tracked.

        Equivalente en libreria a lo que ``sldb.cli.model_utils.registered_model``
        hace para un comando CLI (sin el fallback a stores federados, que el
        Reflector no usa), construido sobre las mismas piezas de librería que
        ``knowledge_base/operations.py`` ya usa: ``sldb.store.io.load_store_index``
        + ``sldb.cli.model_utils.resolve_model_ref`` (el resolvedor inyectado,
        no la capa CLI de un solo disparo).
        """
        store_index = load_store_index(self.store_path)
        entry = next((m for m in store_index.models if m.name == model_name), None)
        if entry is None:
            raise ValueError(f"Model '{model_name}' not registered in store {self.store_path}")
        model_type = resolve_model_ref(entry.model_ref, self.pythonpath)
        return model_type, entry, store_index

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

    @staticmethod
    def _with_status(rendered: str, status: str) -> str:
        """Agrega ``status: <status>`` al frontmatter YA RENDERIZADO, en memoria,
        antes de la única escritura a disco.

        ``AtomDoc`` (``deskops.models:AtomDoc``) no declara un campo ``status``
        en su ``__template__`` (a diferencia de otros modelos de deskops que sí
        lo tienen, p.ej. ``deskops.models.routine``), así que
        ``render_model_markdown`` no tiene forma de emitirlo: no existe una
        llamada de librería de SLDB que produzca un campo que el modelo no
        conoce. Tampoco se puede resolver expresándolo como TAG (el patrón que
        usa ``knowledge_base/operations.py::promote`` para los atoms de la KB
        real, vía ``status:proposed``/``status:active`` en ``tags``): el
        namespace ``status`` no está en el registro de namespaces de atoms de
        deskops (``desk/atoms/tag-namespaces.yaml``, ver
        ``deskops.atom_tags.validate_atom_tag_namespaces``), y agregarlo sería
        una decisión de gobierno de esa taxonomía que no le corresponde tomar
        al Reflector en silencio.

        Antes esto se resolvía escribiendo el ``.md`` ya trackeado en el store,
        para después LEERLO de vuelta del disco y REESCRIBIRLO con la línea
        insertada a mano (``_inject_status``, previo a esta migración: dos
        pasadas de I/O sobre un documento del store). Acá el splice ocurre
        sobre el string ya renderizado en memoria, antes de la única escritura
        (``output_path.write_text``): se elimina el ciclo
        leer-mutar-reescribir, aunque la limitación de fondo —el modelo no
        tiene un campo ``status`` real, ni una tag de status gobernada— sigue
        sin una vía de librería. Ver el reporte sobre ``KnowledgeOperations``
        en el mensaje del commit para lo que faltaría para cerrar esto del
        todo.
        """
        frontmatter_end = rendered.find("\n---\n", 4)
        if frontmatter_end == -1:
            raise ValueError("Could not locate frontmatter boundary in rendered document")
        return f"{rendered[:frontmatter_end]}\nstatus: {status}{rendered[frontmatter_end:]}\n"

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
