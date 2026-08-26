# Handoff — Conversation Flow Editor + KB models

Fecha: 2026-08-26
Rama: `worktree/kb-ui`
Repo: `/home/jp/proyectos/_worktrees/gemini_test-kb-ui`

---

## Qué es este trabajo

UI para visualizar/editar el grafo de flujo conversacional (`ConversationStep`) de un
store SLDB, integrada en la app FastAPI que se deploya (`kb_chat_ui/server.py`).

Interpretación del sistema:
- **sldb** = capa de datos/documentos (los stores `.sldb`, modelos, atoms).
- **deskops** = harness de workflow (no relevante para el runtime del bot).
- Runtime del bot: SLDBReader → ContextCompiler (SLDB+KGDB) → RouterStateMachine →
  Conversador (Gemini) → Tool dispatcher (SQL) → Perfilador async.

---

## Estado del servidor (2º plano)

Corriendo en **puerto 8200** (había zombies del repo original en 8000/8100):
```bash
cd /home/jp/proyectos/_worktrees/gemini_test-kb-ui
python3 -m uvicorn kb_chat_ui.server:app --host 127.0.0.1 --port 8200
```
- Chat:   http://127.0.0.1:8200/
- Editor: http://127.0.0.1:8200/conversation_flow_editor
- Grafo:  http://127.0.0.1:8200/api/flow  (7 nodos, 8 aristas)
- Health: http://127.0.0.1:8200/api/health
- Log: `/tmp/kbserver.log`

Credenciales: `.env` copiado desde `/home/jp/proyectos/gemini_test/.env`
(Vertex AI vía ADC en `~/.config/gcloud/`, project `geminitests1313`). `.env` gitignored.

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

### StepKind (nuevo este sesión)
Enum en `step.py`: `interaccion_simple`, `obtencion_datos`, `handout`, `llamado_tool`.
Campo `kind` (default `interaccion_simple`). Retrocompatible.
- `handout_target` (kind=handout), `tool_ref` (kind=llamado_tool) también nuevos.

---

## Stores SLDB

| Store | Uso | Contenido |
|-------|-----|-----------|
| `tests/knowledge_antonia` | **KB activa del editor/server** | Antonia (PSP Selfix) |
| `tests/knowledge` | Tests | Don Peppe (NO borrar — engrosa después) |
| `knowledge/` | Modelos + meta-atoms | definiciones |

### KB Antonia (`tests/knowledge_antonia/atoms/`) — 20 docs
- **7 steps** (el grafo): saludo, onboarding, registro-estado, evento-adverso,
  agendar-recordatorio, recompra, despedida
- **4 domain**: aplicacion, bienvenida, primeras-semanas, recompra
- **2 rule**: anti-alucinacion, eventos-adversos
- **2 boundary**: clinico, manipulacion
- **1** de cada: self, style, strategy, fallback, tool (agendar_recordatorio)
- **0 traits** ← pendiente crear

### Flujo conversacional (grafo actual)
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
| `conversation_flow_editor/index.html` | UI (React Flow + htm + dagre vía CDN, sin build) |
| `conversation_flow_editor/export_flow.py` | store SLDB → grafo JSON (nodos + aristas de allowed_transitions) |
| `conversation_flow_editor/flow.json` | grafo materializado (también servido en vivo por /api/flow) |
| `kb_chat_ui/server.py` | FastAPI: /, /conversation_flow_editor, /api/flow, /api/chat, /api/atom/{id} |
| `kb_agent/models/knowledge/step.py` | ConversationStep + StepKind |
| `desk/scratch/` | scratch (este handoff, drafts) |

### Regenerar grafo desde el store
```bash
PYTHONPATH=. python conversation_flow_editor/export_flow.py tests/knowledge_antonia
```

---

## Fixes importantes de la sesión (para no repetir)

1. **CSS import ES module** → no se puede `import '...css'`; va como `<link>`.
2. **@xyflow/react versión** → v11 no existe, es `@xyflow/react@12.11.5` (v11 era `reactflow`).
3. **Doble React** → esm.sh bundleaba su propio React; forzar
   `?deps=react@18.3.1&external=react,react-dom` en el importmap.
4. **fetch relativo** → la UI pedía `./flow.json` (404 en /flow.json); ahora `/api/flow`.
5. **Idempotency fail al track** → los .md deben escribirse con el render nativo del
   modelo (`SLDBRenderer().render(doc)`), no a mano. Secciones vacías rompen roundtrip.
6. **Template desalineado** → al agregar secciones al template (Handout Target, Tool),
   TODOS los .md existentes se desalinean. Regenerar todos con el modelo.
7. **KB_ROOT default** → apuntaba a `.sldb_e2e_donpeppe` (movido); ahora `tests/knowledge_antonia`.

### Registrar/actualizar docs en un store
```bash
sldb docs track atoms/<archivo>.md --model <Modelo> --store .sldb --pythonpath <repo_root>
sldb stores update --store tests/knowledge_antonia/.sldb --pythonpath .
```

---

## Tarea EN CURSO (donde quedamos)

**Visualizador de perfilado** (trait profiling).

Concepto acordado: dos capas.
- **SQL `UserTraits`** (`kb_agent/models_sql/identity.py`): user_id, trait_id, confidence,
  source, created_at. Es el perfil por usuario (JSON).
- **SLDB `TraitAtom`**: definición del rasgo (title, description, category, tags
  `user:traits.*`). El `trait_id` de SQL apunta al `id` del TraitAtom.

UI propuesta: panel dividido.
- Izquierda: JSON del perfil (SQL).
- Derecha: fichas TraitAtom (SLDB).
- Interacción: hover/click en un `trait_id` → resalta + scroll a su ficha.

### Bloqueos / decisiones tomadas
- Antonia tiene **0 TraitAtoms** → hay que crearlos.
- Decisión del usuario: **ir con Antonia** (crear traits nuevos). Don Peppe queda
  intacto para tests (NO borrar).
- Pendiente decidir: perfil SQL ¿seed de ejemplo o conectar a `runs/ui-chat.sqlite`?

### Próximo paso inmediato
Crear TraitAtoms para Antonia (ej: "primera vez con inyecciones", "ansioso/a con la
aplicación", "buena adherencia", "dudas sobre efectos"). Formato:
```
---
id: trait-<slug>
title: <titulo>
atom_type: trait
tags:
- user:traits.<slug>
- system:laboratorio-chile
category: <dietary|preference|behavior|demographic>
provenance: null
---

# <titulo>

## Description

<descripcion e implicancia conversacional>
```
Escribir con render nativo del modelo, trackear, `sldb stores update`.

---

## Git

Rama `worktree/kb-ui`. Commits recientes:
- feat(flow): StepKind + flujo Antonia (7 steps) + conversation_flow_editor UI
- Merge conversational-agent-arch → kb-ui (trae server.py, IndexProxies, models)
- feat(server): montar conversation_flow_editor en FastAPI
- fix(server): default KB_ROOT a tests/knowledge_antonia
- fix(editor): fetch /api/flow absoluto

`.env` sin commitear (gitignored, correcto).
