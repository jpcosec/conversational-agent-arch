"""
Tools de retrieval sobre la base de conocimiento SLDB de tutor_apoe.

Estas funciones envuelven el CLI real de `sldb`. No inventan nada:
cada tool corresponde a un comando verificado.

Comandos base:
  sldb find <q> --in semantic --type doc --format json --store .sldb --pythonpath .
  sldb find <q> --in physical --type doc --format json --store .sldb --pythonpath .
  sldb docs show <name> --store .sldb
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# Raíz del repo de conocimiento (donde vive .sldb/)
KB_ROOT = Path("/home/jp/Upla/tutor_apoe")
STORE = ".sldb"


def _run_sldb(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta sldb dentro de KB_ROOT y devuelve (code, stdout, stderr)."""
    proc = subprocess.run(
        ["sldb", *args],
        cwd=str(KB_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


def search_knowledge(query: str, mode: str = "semantic") -> dict:
    """Busca átomos en la base de conocimiento APOS.

    Args:
        query: Término de búsqueda. En modo 'semantic' usa tags namespaced
            (ej: 'topic:schema', 'topic:encapsulation', 'layer:theory',
            'system:apos'). En modo 'physical' busca literalmente en nombres
            de archivo, ids y paths (ej: 'schema', 'genetic-decomposition').
        mode: 'semantic' (por tag/concepto) o 'physical' (por nombre/texto literal).

    Returns:
        dict con 'count' y 'atoms' (lista de {name, path, tags}).
    """
    if mode not in ("semantic", "physical"):
        mode = "semantic"
    code, out, err = _run_sldb(
        ["find", query, "--in", mode, "--type", "doc",
         "--format", "json", "--store", STORE, "--pythonpath", "."]
    )
    if code != 0:
        return {"error": err.strip() or "search failed", "count": 0, "atoms": []}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": "invalid json from sldb", "count": 0, "atoms": []}

    atoms = []
    for r in data.get("results", []):
        if r.get("kind") != "doc":
            continue
        atoms.append({
            "name": r.get("name"),
            "path": r.get("path"),
            "tags": [t for t in r.get("semantic_tags", []) if ":" in t],
        })
    return {"count": len(atoms), "atoms": atoms}


def read_atom(atom_name: str) -> dict:
    """Lee el contenido completo de un átomo de conocimiento.

    Args:
        atom_name: Identificador del átomo (ej:
            'atom-schema-is-a-core-mental-structure-in-apos').
            Se obtiene desde search_knowledge().

    Returns:
        dict con id, title, question (5WH1+), answer, tags, provenance, path.
    """
    code, out, err = _run_sldb(["docs", "show", atom_name, "--store", STORE])
    if code != 0:
        return {"error": err.strip() or "atom not found"}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": "invalid json from sldb"}

    doc = data.get("document", {})
    payload = doc.get("payload", {})
    return {
        "id": payload.get("id"),
        "title": payload.get("title"),
        "question": payload.get("five_wh_one_plus"),
        "answer": payload.get("answer"),
        "tags": payload.get("tags", []),
        "provenance": payload.get("provenance"),
        "path": doc.get("path"),
    }


def list_topics() -> dict:
    """Lista todos los tags/topics disponibles en la base de conocimiento.

    Útil para saber qué se puede buscar antes de llamar search_knowledge.

    Returns:
        dict con 'topics' (lista de {tag, count}) ordenado por frecuencia.
    """
    import yaml  # dependencia ya presente via sldb

    idx = KB_ROOT / STORE / "runtime" / "semantic_index.yaml"
    if not idx.exists():
        return {"error": "semantic index not found", "topics": []}
    data = yaml.safe_load(idx.read_text())
    tags = data.get("tags", {})
    topics = sorted(
        ({"tag": t, "count": len(docs)} for t, docs in tags.items()),
        key=lambda x: (-x["count"], x["tag"]),
    )
    return {"topics": topics}