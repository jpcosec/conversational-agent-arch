# Conversation Flow Editor

UI para visualizar y editar el grafo de flujo conversacional (`ConversationStep`) de un store SLDB.

- **Nodos** = `ConversationStep` (modelo `kb_agent/models/knowledge/step.py`)
- **Aristas** = `allowed_transitions` (tag `conversation:steps.<x>` → step id)
- **Kinds** = `interaccion_simple`, `obtencion_datos`, `handout`, `llamado_tool`

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | UI (React Flow vía CDN, sin build) |
| `export_flow.py` | Lee el store SLDB → genera `flow.json` |
| `flow.json` | Grafo materializado que consume la UI |

## Regenerar el grafo desde el store

```bash
PYTHONPATH=. python frontends/flow_editor/export_flow.py knowledge
# escribe frontends/flow_editor/flow.json
```

## Servir

```bash
python3 -m http.server 8087
# http://localhost:8087/frontends/flow_editor/
```

## Notas

- Sin build step: React 18 + `@xyflow/react` + `htm` + `dagre` desde CDN (importmap).
- Layout automático con dagre (rankdir LR).
- El inspector muestra campos según el `kind` del step.
- Pendiente: botón Save que persista de vuelta a los `.md` del store.
