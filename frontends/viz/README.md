# Visualización de Atoms & Embeddings (ReactFlow)

Grafo 2D interactivo de los átomos de la KB, posicionados por similitud
semántica (embeddings) y coloreados por familia.

## Cómo se sirve

El runtime (`frontends/chat/app.py`) sirve esta UI en vivo, igual que el
Flow Editor y el Taxonomy Explorer:

- `GET /viz` -> este `index.html`.
- `GET /api/viz/graph` -> grafo (nodos/edges) calculado en el momento desde
  la KB del negocio activo (`cfg.kb_root`). Acepta `edge_threshold` y
  `max_edges_per_node` como query params opcionales.

Nunca se leen JSON precalculados: el grafo siempre refleja el estado actual
del store SLDB, sin artefactos de negocio hardcodeados en git.

## Cómo se construye

1. **Exporter** (`export_graph.py`, función `build_graph`): lee átomos +
   embeddings desde la KB, proyecta 768→2D con PCA (SVD, numpy puro), crea
   edges entre pares con alta similitud coseno.
2. **HTML** (`index.html`): ReactFlow vía CDN (ESM), hace `fetch('/api/viz/graph')`
   y `fetch('/api/config')` (nombre del negocio para el header), colorea por
   familia, panel de detalle al click.

## CLI de exportación offline

`export_graph.py` también expone un CLI para volcar el grafo a un JSON fuera
del servidor (debug, artefactos puntuales, CI). Por defecto usa el
`kb_root` resuelto por `project.config.yaml` (vía `load_project_config()`);
pasa `--kb` para apuntar a otra KB:

```bash
python -m frontends.viz.export_graph --out /tmp/graph.json
python -m frontends.viz.export_graph --kb tests/knowledge --out /tmp/graph.json --edge-threshold 0.42 --max-edges-per-node 4
```

## Parámetros

- `--edge-threshold` / `edge_threshold`: similitud coseno mínima para dibujar
  un edge (default `0.55`, ver `DEFAULT_EDGE_THRESHOLD` en `export_graph.py`).
- `--max-edges-per-node` / `max_edges_per_node`: top-k vecinos por nodo
  (default `3`, ver `DEFAULT_MAX_EDGES_PER_NODE`).

Nota: los embeddings jina tienen similitudes moderadas; con KBs pequeñas un
umbral más bajo (p.ej. 0.42) da un grafo más conectado y legible.

## Colores por familia

| Familia | Color |
|---|---|
| `self` | verde salvia |
| `domain` | azul acero |
| `conversation` | ámbar |
| `user` | magenta suave |

Requiere internet (ReactFlow desde esm.sh CDN).
