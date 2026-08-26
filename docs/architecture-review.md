# Architecture Review

Fecha: 2026-08-25

---

## 1. Estado actual del código

### 1.1 Motores cognitivos

| Motor | Responsabilidad real | Dónde vive |
|-------|---------------------|-----------|
| Ontologizador (Compilador) | Trae todos los `atom_type:domain` y `atom_type:rule` sin filtrar por scenario. Produce `CompiledDocument`. | `kb_agent/ontologizador/compiler.py` |
| Conversador | `GeminiConversador.draft_nl()` recibe contexto compilado y llama a Gemini. El prompt está hardcodeado con "Eres el asistente de Don Peppe...". | `kb_agent/orchestrator.py` (GeminiConversador) |
| Perfilador | Post-turno: llama a Gemini para mapear mensaje → trait_id, persiste en UserTraits. Filtra por `atom_type:trait`. | `kb_agent/perfilador/extractor.py` |
| Reflector | Batch: lee ChatHistory, genera atoms con `source:reflector`. Usa tags `topic:ontology`/`topic:rules` para dedup. | `kb_agent/reflector/generator.py` |

### 1.2 Decisión del turno (tool / fallback / NL)

Quién la toma hoy: `draft_conversador_response()` dentro de la `RouterStateMachine`.

```python
def draft_with_real_conversador(compiled_context):
    decision = draft_conversador_response(compiled_context)  # ← decide
    if function_call: return decision
    if fallback: return decision
    return self.conversador.draft_nl(compiled_context)       # ← redacta
```

El conversador y la decisión están en el mismo closure.

### 1.3 Contexto atómico

Quién lo arma hoy: el **orquestador**, re-leyendo el store.

```python
# en _build_turn_context():
full = self.reader.get_doc(atom_id)  # ← re-lectura del store
```

### 1.4 Comportamiento del agente

| Comportamiento | Hoy |
|---------------|-----|
| Prompt del conversador | `"Eres el asistente de la pizzeria Don Peppe..."` hardcodeado en `GeminiConversador.draft_nl()` |
| Frase de fallback | `CANONICAL_FALLBACK_RESPONSE` en `kb_agent/agent.py` |
| Tools | `execute_tool()` con `if name == "crear_reserva"` |
| Steps | `flow_node` se persiste en SQL pero no guía el turno |

### 1.5 Capas de datos

| Capa | Qué contiene | Quién la consulta |
|------|-------------|-------------------|
| SLDB | 13 átomos (`self:*`, `conversation:*`, `domain:*`, `user:traits.*`, tools) | Compilador, Perfilador, Reflector, y **orquestador** (re-lectura) |
| KGDB | Grafo tag-céntrico desde export SLDB | Compilador |
| SQL | Users, SessionState, ChatHistory, UserTraits, Reservas | Orquestador, Perfilador |

### 1.6 Store y doctrina

- `KB-DOCTRINE.md` existe en disco pero **no está en git** (untracked).
- El store tiene 13 átomos en disco, pero el índice SLDB (`documents/AtomDoc.yaml`) está **modificado** (los paths cambiaron de `.sldb_e2e_donpeppe/` a `atoms/`).
- Los archivos `.sldb_e2e_donpeppe/.sldb_e2e_donpeppe/atoms/*.md` están **borrados** del disco (ya no existen).

### 1.7 UI

- `kb_chat_ui/index.html` modificado: migrado de `mesa` a `context`.
- `kb_chat_ui/server.py` nuevo (FastAPI) — **untracked**.
- `tests/e2e/test_ui_backend.py` nuevo — **untracked**.

---

## 2. Objetivo (lo que debería ser)

### 2.1 Responsabilidades

| Motor | Responsabilidad final | Recibe | NO hace |
|-------|----------------------|--------|---------|
| Ontologizador (Compilador) | Dado `pregunta + session_state + traits`, navega SLDB+KGDB, produce `CompiledDocument` cerrado con atoms completos | `question`, `session_state`, `identity_session` | Decidir tipo de turno. Conocer LLM. |
| Orquestador | Decide tipo de turno (NL/tool/fallback). Ejecuta tools. Persiste. Determina step conversacional. | `CompiledDocument` del compilador | Leer SLDB directo. Redactar. |
| Conversador | Redacta texto NL desde contexto compilado. No conoce tools. No decide. | `CompiledDocument` (sin tools) | Decidir. Conocer tools. Navegar KB. |
| Perfilador | Async: aprende traits del turno. Filtra por `user:traits.*`. | Mensaje scrubbeado | Participar del camino crítico. |
| Reflector | Batch: genera atoms desde historial. Usa tags del árbol nuevo. | ChatHistory | Participar del turno. |

### 2.2 Decisión del turno

Quién la toma: el **orquestador**, no la SM ni el conversador.

```
orquestador:
  1. Recibe CompiledDocument del compilador
  2. tools_available = compiled.tools
  3. If compiled.is_empty:
       → responder con texto de conversation:fallback (sin conversador)
  4. If hay tool + intención detectada:
       → ejecutar tool → reinyectar → llamar conversador para redactar
  5. Else:
       → llamar conversador.draft_nl(compiled) para redactar
```

### 2.3 Contexto atómico

Quién lo arma: el **compilador**, una sola vez.

```python
# en compiler.compile():
domain_facts = self._find_atoms("domain")   # tags ya incluidos
rules = self._find_atoms("rule")             # tags ya incluidos
```

Sin re-lectura del store. `CompiledDocument.items` ya trae `{id, title, tags, body, role}` completo.

### 2.4 Comportamiento del agente

| Comportamiento | Fuente | Cómo llega |
|---------------|--------|-----------|
| Identidad | `self:whoami` | Compilador → CompiledDocument → Conversador |
| Estilo | `self:estilo` | Compilador → CompiledDocument → Conversador |
| Límites | `self:limites` | Compilador → CompiledDocument → Conversador |
| Fallback | `conversation:fallback` | Compilador → CompiledDocument → Orquestador |
| Tools | `self:tools` + `atom_type:tool` | Compilador → CompiledDocument → Orquestador |
| Steps | `conversation:steps.*` (KGDB) | Compilador → CompiledDocument → Orquestador |

### 2.5 Quién decide el step conversacional

El **orquestador**.

El compilador solo EXPONE el diagrama (vía KGDB): `steps_under`, `docs_for_tag`,
`allowed_transitions`. No decide el avance.

El orquestador:
- Lee `flow_node` del `SessionState` (SQL)
- Recibe del compilador el step actual + transiciones permitidas
- Decide avance/retroceso/permanencia según intención + resultado de tool
- Persiste el nuevo `flow_node` en `SessionState`

El compilador provee el mapa; el orquestador conduce.

### 2.6 Quién lee la KB directo

| Agente | Lee SLDB | Lee SQL | Lee KGDB |
|--------|----------|---------|----------|
| Compilador | ✅ | ✅ traits | ✅ flow |
| Orquestador | ❌ | ✅ sesión, historial | ❌ |
| Conversador | ❌ | ❌ | ❌ |
| Perfilador | ✅ `user:traits.*` | ✅ UserTraits | ❌ |
| Reflector | ✅ `domain:*` + `rule` | ✅ ChatHistory | ❌ |

### 2.7 Árbol de tags: consumo por agente (target)

| Tag semántico | Quién lo lee de SLDB | Para qué |
|---------------|---------------------|----------|
| `self:whoami` | Compilador | Prompt del conversador |
| `self:estilo` | Compilador | Prompt del conversador |
| `self:limites` | Compilador | Prompt del conversador |
| `self:tools` | Compilador | Tools disponibles para el orquestador |
| `conversation:strategy` | Compilador | Regla de interacción |
| `conversation:fallback` | Compilador | Texto de fallback para el orquestador |
| `conversation:steps.onboarding` | Compilador | Step de onboarding |
| `conversation:steps.booking` | Compilador | Step de reserva |
| `domain:catalogo` | Compilador | Facts del negocio |
| `domain:horarios` | Compilador | Facts del negocio |
| `domain:reglas.reservas` | Compilador | Regla de negocio |
| `user:traits.*` | Perfilador | Catálogo de candidatos |
| `source:*` | — | Metadata |

---

## 3. Brechas: estado actual → objetivo

| # | Aspecto | Estado actual | Objetivo | Prioridad |
|---|---------|--------------|----------|-----------|
| 1 | Decisión tipo de turno | ~~La toma `draft_conversador_response` dentro de la SM~~ | La toma el orquestador via `decide_turn` (policy pura) | ✅ RESUELTO |
| 2 | Contexto atómico | ~~Lo arma el orquestador re-leyendo SLDB (`get_doc`)~~ | El compilador entrega tags+title; el orquestador no re-lee | ✅ RESUELTO |
| 3 | Prompt del conversador | Hardcodeado: "Eres el asistente de Don Peppe..." | Viene de `self:whoami` + `self:estilo` + `self:limites` en el contexto | Alta |
| 4 | Frase de fallback | Hardcodeada en `CANONICAL_FALLBACK_RESPONSE` | Viene de `conversation:fallback` en el contexto | Alta |
| 5 | Tools | `if name == "crear_reserva"` en `execute_tool` | Descubrimiento desde `self:tools` | Media |
| 6 | Perfilador filtro | `fetch("trait")` sin sub-rama | Filtrar por `user:traits.*` además de `atom_type` | Media |
| 7 | Reflector tags | Usa `topic:ontology` / `topic:rules` (viejos) | Usa tags del árbol nuevo (`domain:*`, `conversation:*`) | Media |
| 8 | Steps guían el turno | `flow_node` se persiste pero no guía | Steps navegados por KGDB, guían qué compilar | Media |
| 9 | Store inconsistente | Índices modificados, paths desplazados, KB-DOCTRINE.md sin commitear | Store estable, todo en git | Baja |
| 10 | UI server.py | Existe pero untracked | Commiteado | Baja |
| 11 | Tests UI backend | Existen pero untracked | Commiteados | Baja |

---

## 3.1 Inventario de hardcodeo (scan completo)

| # | Archivo:línea | Hardcodeado | Debe venir de | Estado |
|---|---|---|---|---|
| H1 | `orchestrator.py:61` | Prompt "Eres el asistente de la pizzeria Don Peppe..." | `self:whoami` + `self:estilo` + `self:limites` | ✅ RESUELTO |
| H2 | `agent.py:14` | `CANONICAL_FALLBACK_RESPONSE` | `conversation:fallback` | ✅ RESUELTO |
| H3 | `orchestrator.py:75` | Prompt trait mapper "Analiza el mensaje..." | atom de perfilado / strategy | ✅ ACEPTADO (genérico) |
| H4 | `server.py:40,122,149` | `DEFAULT_SCENARIO = "pizzeria"` | Eliminado; scenario es etiqueta opcional | ✅ RESUELTO |
| H5 | `orchestrator.py:38` | `MODEL = "gemini-2.5-flash"` | `os.getenv("GEMINI_MODEL", ...)` | ✅ RESUELTO |
| H6 | `orchestrator.py:107` | `if name == "crear_reserva"` | `TOOL_HANDLERS` registry | ✅ RESUELTO |

### Resolución H1/H2 (implementada)

El `CompiledDocument` ahora trae el contexto **estructurado por rol semántico**:
- `persona: dict` — extraído de `self:*` (whoami/estilo/limites)
- `strategy: str` — de `conversation:strategy`
- `fallback_text: str` — de `conversation:fallback`
- `domain_facts`/`rules` — SOLO grounding del negocio (`domain:*`), sin ruido self/conversation

`GeminiConversador.draft_nl()` arma el prompt desde `persona` + `strategy`, no
hardcodea identidad. El orquestador usa `fallback_text` de la KB en vez de la
constante. El compilador clasifica por tag (`_extract_persona`, `_extract_by_tag`,
`_grounding_only`). Verificado: el agente responde su identidad desde `self:whoami`.

### Resolución H3-H6 (implementada)

- **H4**: `DEFAULT_SCENARIO = "pizzeria"` eliminado. Coherente con la doctrina
  (una KB = un negocio, el scenario no filtra). `KB_ROOT` ahora via `os.getenv`.
- **H5**: `MODEL` ahora via `os.getenv("GEMINI_MODEL", "gemini-2.5-flash")`.
- **H6**: `execute_tool` usa `TOOL_HANDLERS` (registry name→handler) en vez de
  `if name == "crear_reserva"`. Verificado: reserva real ejecutada via registry.
- **H3**: el prompt del trait mapper es una instrucción de sistema GENÉRICA de
  perfilado ("detecta traits del catálogo"), sin negocio hardcodeado. No viola la
  doctrina; se acepta como lógica reutilizable, no como hardcodeo de negocio.

Todo el hardcodeo de negocio queda eliminado. Verificado: 57/57 tests verde.

---

## 4. Pendientes inmediatos

### 4.1 Commitear lo que está en working tree

```bash
git add docs/architecture.md docs/architecture-review.md
git add kb_chat_ui/server.py
git add tests/e2e/test_ui_backend.py
git add -A
git commit -m "feat: architecture docs, FastAPI server, UI test"
```

### 4.2 Brechas prioritarias (alta) — TODAS RESUELTAS

1. ~~Mover decisión al orquestador~~ ✅ HECHO (policy pura `decide_turn`)
2. ~~Mover contexto atómico al compilador~~ ✅ HECHO (tags+title en CompiledDocument)
3. ~~Deshardcodear prompt desde `self:*`~~ ✅ HECHO
4. ~~Deshardcodear fallback desde `conversation:fallback`~~ ✅ HECHO

### Resolución #1/#2 (implementada)

- **#1 Decisión al orquestador**: nueva función pura `decide_turn(compiled)` en
  `agent.py` que separa DECIDIR de REDACTAR. Devuelve `{kind: tool_call|fallback|nl}`
  sin llamar a Gemini. El orquestador la invoca y conduce la acción (ejecutar
  tool / usar `conversation:fallback` / `draft_nl`). Determinística y testeable
  (5 tests en `test_decide_turn.py`).
- **#2 Contexto atómico sin re-lectura**: `_find_atoms` y `_grounding_only` ahora
  preservan `tags` y `title` en cada atom del `CompiledDocument`. El orquestador
  (`_build_turn_context`) los consume directo, sin `reader.get_doc()`. Un solo
  paso de lectura de SLDB (en el compilador).

### 4.3 Brechas secundarias (media)

5. Tools descubribles desde `self:tools`
6. Perfilador filtra por `user:traits.*`
7. Reflector usa tags del árbol nuevo
8. Steps navegados por KGDB

### 4.4 Store

- Commitear `KB-DOCTRINE.md`
- Estabilizar paths del índice SLDB contra la ubicación real de los átomos