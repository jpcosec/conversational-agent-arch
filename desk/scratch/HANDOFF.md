# Handoff — Conversation Flow Editor + Profiling Viewer

Fecha: 2026-08-26
Rama: `worktree/kb-ui`
Repo: `/home/jp/proyectos/_worktrees/gemini_test-kb-ui`

---

## Qué es esto

Dos UIs integradas en la app FastAPI que se deploya (`kb_chat_ui/server.py`):

1. **Conversation Flow Editor** — visualizar/editar el grafo de `ConversationStep`
2. **Profiling Viewer** — panel de perfilado: `UserTraits` (SQL) ↔ `TraitAtom` (SLDB)

---

## Los 10 modelos de KB (`kb_agent/models/knowledge/`)

Todos heredan de `IndexProxies` (campos offline: summary, embedding, parent, semantic_anchors).

| atom_type | Modelo | Campos propios |
|-----------|--------|----------------|
| **step** | `ConversationStep` | kind, instructions, required_slots, handout_target, tool_ref, allowed_transitions, grounding_atoms, completion_condition |
| domain | `DomainAtom` | answer, five_wh_one_plus, domain_ref |
| rule | `RuleAtom` | answer, conditions, applies_to |
| tool | `ToolAtom` | description, parameters (JSON schema) |
| trait | `TraitAtom` | description, category |
| self | `SelfDeclaration` | statement |
| style | `StyleGuide` | tone, language_register, phrase_preferences, length_guidelines |
| boundary | `CapabilityBoundary` | restriction, conditions, escalation |
| strategy | `StrategyRule` | goal, approach, priorities |
| fallback | `FallbackRule` | fallback_message, conditions |

### StepKind
Enum en `step.py`: `interaccion_simple`, `obtencion_datos`, `handout`, `llamado_tool`.
Campo `kind` (default `interaccion_simple`). Retrocompatible.
- `handout_target` (kind=handout), `tool_ref` (kind=llamado_tool) también nuevos.

---

## Stores SLDB

| Store | Uso | Contenido |
|-------|-----|-----------|
| `tests/knowledge_antonia` | **KB activa del server** | Antonia (PSP Selfix) — **25 docs** |
| `tests/knowledge` | Tests | Don Peppe (intacto para tests) |
| `knowledge/` | Modelos + meta-atoms | definiciones |

### KB Antonia — 25 docs
- **7 steps** (el grafo): saludo, onboarding, registro-estado, evento-adverso, agendar-recordatorio, recompra, despedida
- **4 domain**: aplicacion, bienvenida, primeras-semanas, recompra
- **2 rule**: anti-alucinacion, eventos-adversos
- **2 boundary**: clinico, manipulacion
- **5 traits**: primera-vez, ansioso-aplicacion, buena-adherencia, dudas-efectos, prefiere-recordatorios
- **1** de cada: self, style, strategy, fallback, tool (agendar_recordatorio)

### Flujo conversacional (7 steps)
```
saludo ──┬──→ onboarding ──→ registro-estado
         └────────────────→ registro-estado
                                  │
                  ┌───────────────┴──────────────┐
                  ▼                               ▼
           evento-adverso                 agendar-recordatorio
           (handout)                      (llamado_tool)
                  │                               │
                  ▼                               ▼
              despedida  ◄──────────────────  recompra
```

---

## Archivos clave

| Archivo | Qué es |
|---------|--------|
| `conversation_flow_editor/index.html` | Editor de flujo (ReactFlow + dagre vía CDN, sin build) |
| `conversation_flow_editor/export_flow.py` | store SLDB → grafo JSON |
| `profiling_viewer/index.html` | Visualizador de perfilado (panel split JSON↔fichas) |
| `kb_chat_ui/server.py` | FastAPI: todas las rutas |
| `runs/profiling-demo.sqlite` | DB SQL seed con 3 usuarios ejemplo (7 trait-assignments) |

### Rutas del server
| Ruta | Sirve |
|------|-------|
| `GET /` | Chat UI (index.html) |
| `GET /conversation_flow_editor` | Editor de flujo |
| `GET /api/flow` | Grafo en vivo desde el store (7 nodos, 8 aristas) |
| `GET /api/atom/{id}` | Atom del store |
| `GET /api/chat` | Orquestador (Gemini real) |
| `GET /profiling_viewer` | Visualizador de perfilado |
| `GET /api/profiles` | Perfiles: cruza SQL(Users+UserTraits) + SLDB(TraitAtom) |
| `GET /api/health` | status, kb_root, model |

---

## Perfilado — estructura

**Capa SQL** (UserTraits en `kb_agent/models_sql/identity.py`):
```
user_id | trait_id            | confidence | source   | created_at
--------|---------------------|------------|----------|------------
42      | trait-antonia-primera-vez | 0.95  | perfilador
```

**Capa SLDB** (TraitAtom en `tests/knowledge_antonia/atoms/`):
```
id: trait-antonia-primera-vez
title: Primera vez con inyecciones
description: Paciente que nunca se ha auto-inyectado...
category: behavior
tags: [user:traits.primera_vez, system:laboratorio-chile]
```

SQL `trait_id` apunta a SLDB `TraitAtom.id` (como FK lógica).

### Endpoint /api/profiles
```json
{
  "users": [
    { "user_id": 1, "external_id": "wa:+56911111111",
      "traits": [{"trait_id": "trait-antonia-primera-vez", "confidence": 0.95, "source": "perfilador"}, ...] },
    ...
  ],
  "fichas": { "trait-antonia-primera-vez": {"title":"...", "description":"...", "category":"...", ...} },
  "missing_fichas": []
}
```
`missing_fichas`: trait_ids referenciados desde SQL que NO tienen TraitAtom en SLDB (detecta roturas).

---

## Fixes importantes de la sesión

1. **CSS import ES module** → no se puede `import '...css'`; va como `<link>`.
2. **@xyflow/react versión** → v11 no existe, es `@xyflow/react@12.11.5` (v11 era `reactflow`).
3. **Doble React** → esm.sh bundleaba su propio React; forzar `?deps=react@18.3.1&external=react,react-dom`.
4. **fetch relativo** → usar `/api/flow`, no `./flow.json`.
5. **Idempotency fail al track** → los .md deben escribirse con el render nativo del modelo (`SLDBRenderer().render(doc)`), no a mano. Secciones vacías rompen roundtrip.
6. **Template desalineado** → al agregar secciones al template, regenerar TODOS los .md del store.
7. **KB_ROOT default** → apuntaba a `.sldb_e2e_donpeppe` (movido); ahora `tests/knowledge_antonia`.

---

## Comandos útiles

```bash
# levantar server
setsid python3 -m uvicorn kb_chat_ui.server:app --host 127.0.0.1 --port 8200 > /tmp/kb2.log 2>&1 < /dev/null &

# regenerar grafo
PYTHONPATH=. python conversation_flow_editor/export_flow.py tests/knowledge_antonia

# trackear/actualizar store
sldb docs track atoms/<archivo>.md --model <Modelo> --store .sldb --pythonpath <repo_root>
sldb stores update --store tests/knowledge_antonia/.sldb --pythonpath .
```

---

## Tareas pendientes / ideas
- [ ] Guardar cambios del editor de flujo (inspector → UPDATE en SLDB)
- [ ] Interacción con el visualizador de flujo (seleccionar paso → ver sus grounding_atoms)
- [ ] Don Peppe: engrosar su KB (cuando toque)
- [ ] Conectar perfil SQL real (no seed de demo) — apuntar a `runs/ui-chat.sqlite` del orquestador

---

## Git

Rama `worktree/kb-ui`. Commits recientes:
```
5c909ff feat(profiling): visualizador UserTraits(SQL)↔TraitAtom(SLDB) + 5 traits Antonia + /api/profiles
e19254a fix(editor): fetch /api/flow (absoluto) en vez de ./flow.json relativo
3d4d89f chore(antonia): reindex store (index regeneration)
99478a5 feat(server): montar conversation_flow_editor en la app FastAPI
33ce5c9 Merge 'conversational-agent-arch' into worktree/kb-ui
e239b09 fix(server): default KB_ROOT a tests/knowledge_antonia
eb5b4c7 feat(flow): StepKind + flujo Antonia (7 steps) + conversation_flow_editor UI
```

`.env` gitignored (copiado desde `/home/jp/proyectos/gemini_test/.env`).
Credenciales: Vertex AI vía ADC (`~/.config/gcloud/application_default_credentials.json`).

Handoff: `desk/scratch/HANDOFF.md`.