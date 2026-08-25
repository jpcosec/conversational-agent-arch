"""SLDB reader que usa la API real de la librería sldb.

En vez de hacer glob de archivos .md y parsear frontmatter a mano,
consulta el store indexado de SLDB mediante búsqueda semántica y
extrae los campos ya resueltos por el modelo.

Uso:
    reader = SLDBReader(kb_root=Path(".sldb_e2e_donpeppe"), store_name=".sldb")
    atoms = reader.find("domain:pizzeria")      # búsqueda semántica
    atom  = reader.get_doc("atom-donpeppe-carta")  # fields ya resueltos
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sldb.cli.commands.find import SearchRecord, iter_search_records, search_records


class SLDBReader:
    """Lee documentos SLDB usando la librería real, no file-globbing manual."""

    def __init__(self, kb_root: str | Path, store_name: str = ".sldb") -> None:
        kb_root = Path(kb_root).resolve()
        self._store_path = kb_root / store_name
        self._pythonpath = str(kb_root)
        self._records: list[SearchRecord] = list(
            iter_search_records(self._store_path, pythonpath=self._pythonpath)
        )

    def find(self, term: str, search_in: str = "semantic") -> list[dict[str, Any]]:
        """Busca registros por término semántico (domain:pizzeria, atom_type:rule, etc.)."""
        matched = search_records(self._records, term, search_in=search_in)
        return [self._doc_payload(r) for r in matched if r.kind == "doc"]

    def find_fields(self, term: str, search_in: str = "semantic") -> list[dict[str, Any]]:
        """Busca registros de cualquier tipo (doc, section, field) para queries finas."""
        matched = search_records(self._records, term, search_in=search_in)
        payloads = []
        for r in matched:
            d = r.as_dict() if hasattr(r, "as_dict") else {}
            d["payload"] = r.payload
            payloads.append(d)
        return payloads

    def get_doc(self, doc_id: str) -> dict[str, Any] | None:
        """Obtiene los campos resueltos de un documento por su id."""
        for r in self._records:
            if r.kind == "doc" and r.name == doc_id:
                return self._doc_payload(r)
        return None

    def fetch(self, atom_type: str) -> list[dict[str, Any]]:
        """Compatibilidad con API anterior: filtra por atom_type en tags."""
        return self.find(f"atom_type:{atom_type}", search_in="semantic")

    def refresh(self) -> None:
        """Recarga el índice (útil si cambian los documentos fuente)."""
        self._records = list(
            iter_search_records(self._store_path, pythonpath=self._pythonpath)
        )

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _doc_payload(r: SearchRecord) -> dict[str, Any]:
        payload = dict(r.payload or {})
        payload["id"] = r.name
        payload["tags"] = r.semantic
        payload["path"] = str(r.path) if r.path else None
        return payload

    @staticmethod
    def _matches_tag(payload: dict[str, Any], tag: str) -> bool:
        tags = payload.get("tags", [])
        return any(t == tag or t.startswith(f"{tag}.") for t in tags)