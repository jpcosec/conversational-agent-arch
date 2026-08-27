"""SLDB reader que usa la API real de la librería sldb.

En vez de hacer glob de archivos .md y parsear frontmatter a mano,
consulta el store indexado de SLDB vía la capa de LIBRERÍA
(``sldb.store.query.load_runtime_documents``), no la capa CLI
(``sldb.cli.commands.find`` / ``sldb.cli.graph_ops``), pensada para un
proceso de un solo disparo que reescanea el store completo (globs +
AST de secciones) en cada llamada. ``load_runtime_documents`` deja cada
documento con su payload ya resuelto (``extract_model_data`` corrido una
sola vez) en una sola pasada, sin ese costo. Mismo patrón que
``knowledge_base/operations.py::_find_records`` (ver commit 310e684).

Uso:
    reader = SLDBReader(kb_root=Path("tests/knowledge"), store_name=".sldb")
    atoms = reader.find("domain:pizzeria")      # búsqueda semántica
    atom  = reader.get_doc("atom-donpeppe-carta")  # fields ya resueltos
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sldb.cli.model_utils import resolve_model_ref
from sldb.store.query import load_runtime_documents
from sldb.store.query_engine.models import RuntimeDocument


class SLDBReader:
    """Lee documentos SLDB usando la librería real, no file-globbing manual."""

    def __init__(self, kb_root: str | Path, store_name: str = ".sldb") -> None:
        kb_root = Path(kb_root).resolve()
        self._store_path = kb_root / store_name
        self._pythonpath = str(kb_root)
        self._records: list[RuntimeDocument] = self._load()

    def find(self, term: str, search_in: str = "semantic") -> list[dict[str, Any]]:
        """Busca documentos por término semántico (domain:pizzeria, atom_type:rule, etc.)."""
        return [self._doc_payload(r) for r in self._records if self._matches(r, term, search_in)]

    def find_fields(self, term: str, search_in: str = "semantic") -> list[dict[str, Any]]:
        """Busca registros de campo (no solo documentos) para queries finas.

        Nadie en el runtime actual llama a este método (verificado por grep
        sobre kb_agent/frontends/tests); se mantiene por compatibilidad de
        firma/forma con el reader viejo, pero reimplementado sobre la MISMA
        fuente que ``find``/``get_doc`` (``load_runtime_documents``): un
        registro por campo hoja del payload ya resuelto de cada documento
        que matchea `term`, sin reparsear AST de secciones como hacía la
        capa CLI (``sldb.cli.graph_ops``).
        """
        results: list[dict[str, Any]] = []
        for r in self._records:
            if not self._matches(r, term, search_in):
                continue
            tags = list(r.semantic_tags or [])
            for field_path, value in self._flatten(r.payload):
                results.append({
                    "kind": "field",
                    "model": r.model_name,
                    "doc": r.name,
                    "field": field_path,
                    "path": r.path,
                    "title": r.payload.get("title"),
                    "value": value,
                    "semantic": tags,
                    "payload": r.payload,
                })
        return results

    def get_doc(self, doc_id: str) -> dict[str, Any] | None:
        """Obtiene los campos resueltos de un documento por su id."""
        for r in self._records:
            if r.name == doc_id:
                return self._doc_payload(r)
        return None

    def fetch(self, atom_type: str) -> list[dict[str, Any]]:
        """Selecciona atoms por MODELO tipado (type.knowledge.<tipo>).

        La KB usa modelos tipados: ``atom_type`` es un campo del modelo, no un
        tag. La selección es por el eje ``type.knowledge.<tipo>`` derivado del
        ``__semantics__`` de cada modelo.
        """
        return self.find(f"type.knowledge.{atom_type}", search_in="semantic")

    def refresh(self) -> None:
        """Recarga el índice (útil si cambian los documentos fuente)."""
        self._records = self._load()

    # ── helpers ──────────────────────────────────────────────

    def _load(self) -> list[RuntimeDocument]:
        return load_runtime_documents(self._store_path, resolve_model_ref, pythonpath=self._pythonpath)

    @staticmethod
    def _matches(r: RuntimeDocument, term: str, search_in: str) -> bool:
        haystacks: list[str] = []
        if search_in in {"physical", "both"}:
            haystacks.extend([r.name, r.path, f"{r.model_name}/{r.name}"])
        if search_in in {"semantic", "both"}:
            haystacks.extend(r.semantic_tags or [])
        return any(term == h or term in h for h in haystacks if h)

    @staticmethod
    def _flatten(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
        if isinstance(payload, dict):
            pairs: list[tuple[str, Any]] = []
            for key, value in payload.items():
                path = f"{prefix}.{key}" if prefix else key
                pairs.extend(SLDBReader._flatten(value, path))
            return pairs
        return [(prefix, payload)]

    @staticmethod
    def _doc_payload(r: RuntimeDocument) -> dict[str, Any]:
        payload = dict(r.payload or {})
        payload["id"] = r.name
        payload["tags"] = list(r.semantic_tags or [])
        payload["path"] = str(r.path) if r.path else None
        return payload
