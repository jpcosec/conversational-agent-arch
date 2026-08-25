# Architecture TODO

Pendientes priorizados para cerrar la fase actual del agente conversacional.

---

## Prioridad alta (rompen la arquitectura)

### A1. Mover decisión tool/fallback/NL al orquestador

**Hoy:** `draft_conversador_response()` dentro de la `RouterStateMachine` decide si es tool, fallback o NL. El conversador y la decisión están en el mismo closure.

**Objetivo:** El orquestador decide. `RouterStateMachine` solo ejecuta la mecánica del turno (pausa/reanuda). El conversador solo redacta.

**Archivos:**
- `kb_agent/orchestrator.py` — mover lógica de decisión desde el closure `draft_with_real_conversador` al flujo principal de `handle_turn`.
- `kb_agent/agent.py` — `draft_conversador_response` queda como helper del orquestador, no de la SM.

### A2. Mover `_build_turn_context` al compilador

**Hoy:** El orquestador re-lee el store con `reader.get_doc(id)` por cada atom para completar `title` y `tags`.

**Objetivo:** El compilador entrega atoms completos (`id, title, tags, body, role`) en el `CompiledDocument`. El orquestador no toca SLDB.

**Archivos:**
- `kb_agent/ontologizador/compiler.py` — `_find_atoms` conserva `title` y `tags` desde el payload de SLDB.
- `kb_agent/ontologizador/compiled_document.py` — `domain_facts` y `rules` incluyen `title` y `tags`.
- `kb_agent/orchestrator.py` — eliminar `_build_turn_context`, usar los datos que ya vienen del compilador.

### A3. Deshardcodear prompt del conversador desde `self:*`

**Hoy:** `GeminiConversador.draft_nl()` tiene el prompt hardcodeado:
```python
prompt = "Eres el asistente de la pizzeria Don Peppe..."
```

**Objetivo:** El prompt se construye desde los átomos `self:whoami`, `self:estilo`, `self:limites` que el compilador incluye en el `CompiledDocument`.

**Archivos:**
- `kb_agent/orchestrator.py` (GeminiConversador) — construir prompt desde `compiled_context.get("self.*")`.
- `kb_agent/ontologizador/compiler.py` — asegurar que `self:*` se incluya en `rules` (hoy ya entra pero hay que verificar el rol).

### A4. Deshardcodear fallback desde `conversation:fallback`

**Hoy:** `CANONICAL_FALLBACK_RESPONSE` en `kb_agent/agent.py`.

**Objetivo:** El texto de fallback viene del átomo `conversation:fallback` que el compilador incluye en el `CompiledDocument`. Cuando `is_empty`, el orquestador usa ese texto.

**Archivos:**
- `kb_agent/agent.py` — eliminar `CANONICAL_FALLBACK_RESPONSE`.
- `kb_agent/orchestrator.py` — leer fallback desde `compiled_context.rules` filtrando por tag `conversation:fallback`.

---

## Prioridad media (desalineación funcional)

### B1. Tools descubribles desde `self:tools`

**Hoy:** `execute_tool()` es un `if name == "crear_reserva"`.

**Objetivo:** Las tools se ejecutan por descubrimiento desde el schema que viene en `CompiledDocument.tools`. El orquestador itera tools, matchea por nombre y delega a un dispatcher genérico.

**Archivos:**
- `kb_agent/orchestrator.py` — `execute_tool()` debe ser genérico, no un if.

### B2. Perfilador filtra por `user:traits.*`

**Hoy:** `self.reader.fetch("trait")` sin sub-rama.

**Objetivo:** Además de `atom_type:trait`, filtrar por `user:traits.*` en los tags semánticos.

**Archivos:**
- `kb_agent/perfilador/extractor.py` — `_load_candidates()`.

### B3. Reflector usa tags del árbol nuevo

**Hoy:** Usa `topic:ontology` / `topic:rules` (tags que no existen en el árbol nuevo).

**Objetivo:** Usar `domain:*` y `conversation:*` del árbol canónico.

**Archivos:**
- `kb_agent/reflector/generator.py` — `_existing_normalized_texts()` y `_topic_tag_for_type()`.

### B4. Steps navegados por KGDB (flow_node resuelto desde grafo)

**Hoy:** `flow_node` se persiste pero el compilador deriva el step del primer step disponible, no del grafo real.

**Objetivo:** Que `_augment_from_kgdb` navegue `conversation:steps.*` en KGDB para determinar el step actual, transiciones y grounding.

**Archivos:**
- `kb_agent/ontologizador/kgdb_reader.py` — métodos helper.
- `kb_agent/ontologizador/compiler.py` — `_augment_from_kgdb()`.

---

## Prioridad baja (falta de feature)

### C1. Commitear cambios actuales

Archivos en working tree sin commitear (server.py, test_ui_backend, cambios en compiler/kgdb/orchestrator/index.html, docs).

### C2. Onboarding detecta primer turno

Traer `conversation:steps.onboarding` condicionalmente cuando el usuario no tiene historial.

### C3. Explorador de KB en la UI

Listado de atoms independiente del turno actual.

### C4. Store inconsistente

Índices SLDB modificados, paths desplazados, `KB-DOCTRINE.md` sin commitear. Estabilizar.

---

## Orden sugerido

1. Commitear estado actual (C1).
2. A1 + A2 (decisión y contexto atómico — son la misma refactor).
3. A3 + A4 (deshardcodear comportamiento).
4. B1, B2, B3, B4 (desalineaciones).
5. C2, C3, C4 (features).