# Visualización de Atoms & Embeddings (ReactFlow)

Grafo 2D interactivo de los átomos de la KB, posicionados por similitud
semántica (embeddings) y coloreados por familia.

## Cómo se construye

1. **Exporter** (`export_graph.py`): lee átomos + embeddings desde la KB,
   proyecta 768→2D con PCA (SVD, numpy puro), crea edges entre pares con
   alta similitud coseno. Salida: JSON de nodos/edges.
2. **HTML** (`index.html`): ReactFlow vía CDN (ESM), carga el JSON,
   colorea por familia, panel de detalle al click.

## Regenerar los grafos

```bash
python -m viz.export_graph --kb tests/knowledge          --out viz/graph-donpeppe.json --edge-threshold 0.42 --max-edges-per-node 4
python -m viz.export_graph --kb tests/knowledge_antonia  --out viz/graph-antonia.json  --edge-threshold 0.42 --max-edges-per-node 4
python -m viz.export_graph --kb knowledge                --out viz/graph-reusable.json --edge-threshold 0.42 --max-edges-per-node 4
```

## Ver

```bash
cd viz && python -m http.server 8899
# abrir http://localhost:8899/
```

Requiere internet (ReactFlow desde esm.sh CDN).

## Colores por familia

| Familia | Color |
|---|---|
| `self` | violeta |
| `conversation` | celeste |
| `domain` | verde |
| `user` | ámbar |

## Parámetros

- `--edge-threshold`: similitud coseno mínima para dibujar un edge (default 0.55).
- `--max-edges-per-node`: top-k vecinos por nodo (default 3).

Nota: los embeddings jina tienen similitudes moderadas; 0.42 da un grafo
conectado y legible.
