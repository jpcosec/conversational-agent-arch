"""Exporta atoms + embeddings a un grafo 2D para visualizar con ReactFlow.

Proyecta los embeddings 768-dim a 2D via PCA (numpy puro, sin sklearn),
colorea por familia semantica y crea edges entre pares con alta similitud
coseno. Escribe un JSON consumido por el HTML de ReactFlow.

El runtime lo consume en vivo via ``GET /api/viz/graph`` (ver
``frontends/chat/app.py``); este CLI queda para exportar un JSON offline
(debug, artefactos, ci) sin depender del servidor.

Uso:
    python -m frontends.viz.export_graph --out frontends/viz/graph.json
    python -m frontends.viz.export_graph --kb tests/knowledge --out /tmp/graph.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from knowledge_base.operations import ALL_MODELS
from sldb.cli.model_utils import resolve_model_ref
from sldb.store.query import load_runtime_documents

# Paleta alineada con kb-ui (taxonomy_explorer).
FAMILY_COLORS = {
    "self": "#7cba7c",          # verde salvia
    "domain": "#7fb3d5",        # azul acero
    "conversation": "#e6a85c",  # ambar
    "user": "#c97db9",          # magenta suave
    None: "#9aa7bd",            # gris azulado (sin familia)
}

#: Defaults compartidos entre el CLI y GET /api/viz/graph (frontends/chat/app.py).
DEFAULT_EDGE_THRESHOLD = 0.55
DEFAULT_MAX_EDGES_PER_NODE = 3


def _load_atoms(kb: str, pythonpath: str) -> list[dict]:
    """Carga atoms + embeddings vía la capa de librería de SLDB.

    Antes llamaba a ``KnowledgeOperations._find_records()`` (un método
    "privado" de otro módulo) y después volvía a leer/parsear cada ``.md``
    con ``extract_model_data`` -- un segundo parseo redundante, porque
    ``_find_records()`` ya trae el payload resuelto por documento (vía
    ``load_runtime_documents`` internamente). ``KnowledgeOperations`` no
    expone una API pública que devuelva "todos los docs de todos los
    modelos con su payload" (sus métodos públicos son búsquedas puntuales:
    ``show``, ``explore_multi``, ``fetch``-equivalentes por tipo), así que
    en vez de forzar ese caso por una API pensada para otra cosa, esto usa
    directamente la misma capa de librería que ``KnowledgeOperations``
    usa por dentro (``sldb.store.query.load_runtime_documents``), sin pasar
    por ``knowledge_base`` en absoluto.
    """
    by_class = {cls.__name__.lower(): cls for cls in ALL_MODELS}
    store_path = Path(kb).resolve() / ".sldb"
    docs = load_runtime_documents(store_path, resolve_model_ref, pythonpath=pythonpath)

    atoms = []
    for d in docs:
        model_cls = by_class.get((d.model_name or "").lower())
        if model_cls is None:
            continue
        emb = d.payload.get("embedding")
        if not emb:
            continue
        family = model_cls.family()
        atoms.append({
            "id": d.name,
            "title": d.payload.get("title", d.name),
            "summary": d.payload.get("summary", ""),
            "model": model_cls.__name__,
            "family": family,
            "tags": d.payload.get("tags", []),
            "embedding": np.asarray(emb, dtype=np.float64),
        })
    return atoms


def _pca_2d(mat: np.ndarray) -> np.ndarray:
    """PCA a 2D via SVD. mat: (n, d) -> (n, 2)."""
    centered = mat - mat.mean(axis=0, keepdims=True)
    # SVD: filas de Vt son componentes principales
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vt[:2].T
    return coords


def _normalize_coords(coords: np.ndarray, scale: float = 900.0) -> np.ndarray:
    """Reescala a un canvas [0, scale] en ambos ejes."""
    mn = coords.min(axis=0, keepdims=True)
    mx = coords.max(axis=0, keepdims=True)
    span = np.where((mx - mn) == 0, 1.0, mx - mn)
    return (coords - mn) / span * scale


def _cosine_sim_matrix(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    unit = mat / norms
    return unit @ unit.T


def build_graph(kb: str, pythonpath: str, edge_threshold: float, max_edges_per_node: int) -> dict:
    atoms = _load_atoms(kb, pythonpath)
    if not atoms:
        return {"nodes": [], "edges": [], "meta": {"count": 0}}

    mat = np.vstack([a["embedding"] for a in atoms])
    coords = _normalize_coords(_pca_2d(mat))
    sims = _cosine_sim_matrix(mat)

    nodes = []
    for i, a in enumerate(atoms):
        nodes.append({
            "id": a["id"],
            "position": {"x": float(coords[i, 0]), "y": float(coords[i, 1])},
            "data": {
                "label": a["title"],
                "summary": a["summary"],
                "model": a["model"],
                "family": a["family"] or "none",
                "tags": a["tags"],
            },
            "style": {
                "background": "rgba(18,18,26,.95)",
                "color": "#f5f0e8",
                "border": f"2px solid {FAMILY_COLORS.get(a['family'], FAMILY_COLORS[None])}",
                "borderLeft": f"4px solid {FAMILY_COLORS.get(a['family'], FAMILY_COLORS[None])}",
                "borderRadius": "12px",
                "padding": "7px 13px",
                "fontSize": "11px",
                "width": 160,
            },
        })

    edges = []
    n = len(atoms)
    for i in range(n):
        # top-k vecinos por similitud (excluye si mismo)
        order = np.argsort(-sims[i])
        added = 0
        for j in order:
            if j == i:
                continue
            s = float(sims[i, j])
            if s < edge_threshold:
                break
            if added >= max_edges_per_node:
                break
            a_id, b_id = atoms[i]["id"], atoms[j]["id"]
            key = tuple(sorted((a_id, b_id)))
            eid = f"{key[0]}__{key[1]}"
            if any(e["id"] == eid for e in edges):
                continue
            edges.append({
                "id": eid,
                "source": a_id,
                "target": b_id,
                "data": {"similarity": round(s, 3)},
                "style": {"stroke": "#3a4358", "strokeWidth": max(0.5, (s - edge_threshold) * 8)},
            })
            added += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "count": n,
            "edge_threshold": edge_threshold,
            "families": sorted({(a["family"] or "none") for a in atoms}),
            "kb": kb,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Exporta atoms+embeddings a grafo ReactFlow.")
    ap.add_argument("--kb", default=None, help="Ruta de la KB (default: kb_root de project.config.yaml)")
    ap.add_argument("--pythonpath", default=".", help="Pythonpath para modelos")
    ap.add_argument("--out", required=True, help="Ruta del JSON de salida")
    ap.add_argument("--edge-threshold", type=float, default=DEFAULT_EDGE_THRESHOLD, help="Similitud coseno minima para edge")
    ap.add_argument("--max-edges-per-node", type=int, default=DEFAULT_MAX_EDGES_PER_NODE, help="Edges maximos por nodo")
    args = ap.parse_args()

    kb = args.kb
    if kb is None:
        from kb_agent.project_config import load_project_config

        kb = str(load_project_config().kb_root)

    graph = build_graph(kb, args.pythonpath, args.edge_threshold, args.max_edges_per_node)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Grafo: {graph['meta']['count']} nodos, {len(graph['edges'])} edges -> {out}")


if __name__ == "__main__":
    main()
