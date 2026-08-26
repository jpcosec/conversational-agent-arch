---
id: atom-embeddings-como-layout-no-vista
title: "Embeddings: layout de Mindmap, no vista separada"
status: active
tags: [decision, ui, mindmap, embeddings]
---

## Decisión

Embeddings (ex `frontends/viz/`) NO es una vista separada. Es un **layout más**
dentro de Mindmap (`/mindmap`), seleccionable por hotkey 3 o botón.

## Por qué

- React Flow es la base común de ambas: taxonomy (árbol jerárquico) y viz
  (grafo PCA 2D) ya usan `@xyflow/react` + `htm` + `dagre` con importmap
  idéntico. Fusionarlas es trivial: cambiar `nodes` y `edges` dinámicamente
  según el layout activo.
- La vista embeddings se beneficia de la infraestructura de mindmap (sidebar
  filtro, node search, node toolbar, collapse, drag-handle) sin duplicar.
- El usuario puede cambiar de layout sin cambiar de ruta — explorar la misma
  KB en forma jerárquica o por similitud semántica sin perder contexto.
- cross-family links se ven naturalmente en embeddings por la proximidad PCA.

## Alternativas descartadas

- **Vista separada `/embeddings`**: duplica infraestructura (sidebar, search,
  toolbar, hotkeys). El usuario pierde contexto al cambiar de vista para ver
  la misma data desde otro ángulo.
- **Toggle overlay sobre árbol**: complejidad técnica (posiciones PCA no
  alineadas con dagre), confusión visual al superponer dos sistemas de
  coordenadas.

## Referencias

- UI-GUIDE.md §4.1 (tres layouts: tree, topdown, embeddings)
- seed-ui-correcciones-y-vistas.md §6 (fusión taxonomía+embeddings)
- frontends/viz/ (README.md y export_graph.py se mantienen como módulo de backend)