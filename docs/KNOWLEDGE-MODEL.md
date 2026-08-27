# Modelo de knowledge: documentos, relaciones, agentes y SQL

Estado: **descripción del sistema actual + inconsistencias** (2026-08-27).
Escrito a mano. Complementa `AGENT-CONTRACTS.md` (qué recibe cada agente);
este documento cubre **qué son los documentos, cómo se relacionan entre sí,
y cómo se conectan con los agentes y con SQL**.

Todo lo que dice "hoy" está verificado contra `dev @ 5e01207` (§9).

---

## 1. Qué es un documento de knowledge

Un documento es un archivo Markdown con **frontmatter YAML tipado + cuerpo
en secciones**. El frontmatter lleva los campos indexables; el cuerpo lleva
los campos de texto largo, uno por sección `## `. Ambos son campos del mismo
modelo Pydantic: la sección `## Answer` *es* el campo `answer`.

```markdown
---
id: atom-antonia-aplicacion
title: Administración de Selfix
five_wh_one_plus: how
atom_type: domain            # ← tipo: decide qué modelo lo valida
tags:
- domain:tratamiento
- conversation:steps.recompra
- system:laboratorio-chile
domain_ref: psp-selfix
provenance: null
summary: Cómo administrar Selfix correctamente; ...
embedding: [-0.022079, ...]  # 768d, jina-embeddings-v2-base-es
parent: null
semantic_anchors: null
---

# Administración de Selfix

## Answer

Recordar la aplicación semanal según el día y hora de la persona. ...
```

El tipo lo da `atom_type` en el frontmatter, **no la carpeta**: los 71
documentos viven planos en `knowledge/atoms/`. El nombre de archivo sigue
la convención `<prefijo>-antonia-<slug>.md` donde el prefijo coincide con el
tipo (`atom-`, `rule-`, `step-`, `trait-`, `gate-`, ...), pero eso es
convención, no lo que lee el sistema.

### 1.1 Ciclo de vida: de la clase al índice

```mermaid
flowchart LR
    PY["kb_agent/models/knowledge/*.py<br/>11 clases Pydantic<br/>(campos + __template__ + semantics)"]
    REG["knowledge/.sldb/core/models/*.yaml<br/>registro: model_ref → índice"]
    MD["knowledge/atoms/*.md<br/>71 instancias"]
    IDX["knowledge/.sldb/core/documents/*.yaml<br/>índice por modelo (hash, path)"]
    RT["knowledge/.sldb/runtime/<br/>sections/, semantic_index.yaml,<br/>semantic_dag.yaml"]
    SLDB["SLDBReader<br/>find / find_fields / fetch / get_doc"]
    KGDB["KGDBReader<br/>grafo networkx: docs + tags + aristas"]

    PY -->|"sldb bootstrap"| REG
    MD -->|"sldb docs track<br/>(valida contra la clase)"| IDX
    REG --> IDX
    IDX --> RT
    RT --> SLDB
    RT --> KGDB
```

- **Clase** (`*.py`): declara campos, cuáles son obligatorios, el
  `__template__` que dicta el layout del `.md`, y `semantics`
  (`type.knowledge.<tipo>`, `workspace.knowledge`).
- **Registro** (`core/models/*.yaml`): une nombre de modelo con
  `model_ref` importable y con su índice de documentos.
- **Instancia** (`*.md`): se trackea con `sldb docs track`, que la valida
  contra la clase. Un `.md` que no cumple el modelo no entra al índice.
- **Runtime**: `semantic_index.yaml` (búsqueda por semantics/tags),
  `semantic_dag.yaml` (jerarquía de tags: `conversation:steps` →
  `conversation:steps.onboarding`, ...), `sections/` (cuerpo por sección).
- **Readers**: `SLDBReader` busca por término semántico; `KGDBReader`
  construye un grafo dirigido con documentos y tags como nodos.

**Hoy — deuda:** los `path:` en `core/models/*.yaml` apuntan a
`/home/jp/proyectos/_worktrees/gemini_test-kb/...`, un checkout que ya no
existe. Se resuelve por `model_ref`, así que funciona, pero es residuo.

---

## 2. Campos comunes a todos los documentos

Todos los modelos heredan de `IndexProxies` + `StructuredNLDoc`. Campos
compartidos (`*` = obligatorio):

| Campo | Tipo | Para qué | Hoy |
|---|---|---|---|
| `id` * | str | identidad; es lo que SQL y otros docs referencian | ok |
| `title` * | str | nombre legible; se renderiza como `# título` | ok |
| `tags` | `list[ns:valor]` | **relación horizontal principal**; búsqueda | ok, 71/71 |
| `summary` * | str | resumen corto para índice y listados | ok, 71/71 |
| `embedding` | `list[float]` | vector 768d para similitud contra la query | poblado 71/71, **nadie lo lee** |
| `parent` | str (id) | jerarquía | 23/71 con padre, sin lector |
| `semantic_anchors` | `list[str]` | anclas semánticas explícitas | **vacío en 71/71** |
| `provenance` | str | de dónde salió (`source:reflector`, sesión, etc.) | 60/71 |

`domain_ref` (37/71) y `five_wh_one_plus` (43/71) son de algunos modelos,
no de la base. `domain_ref` vale siempre `psp-selfix`: hoy no discrimina.

---

## 3. Catálogo: los 11 tipos de documento

| Tipo (`atom_type`) | Modelo | N | Campos propios (`*` obligatorio) | Secciones del cuerpo | Rol |
|---|---|---|---|---|---|
| `domain` | `DomainAtom` | 32 | `five_wh_one_plus`*, `answer`*, `domain_ref` | Answer | hecho del negocio; grounding de respuestas |
| `rule` | `RuleAtom` | 11 | `five_wh_one_plus`*, `answer`*, `conditions`, `applies_to` | Answer, Conditions | regla condicional (clasificación, seguridad, anti-alucinación) |
| `step` | `ConversationStep` | 11 | `kind`, `instructions`*, `required_slots`, `handout_target`, `tool_ref`, `allowed_transitions`, `grounding_atoms`, `completion_condition`, `domain_ref` | Instructions, Required Slots, Handout Target, Tool, Allowed Transitions, Grounding Atoms, Completion Condition | nodo del flujo conversacional |
| `trait` | `TraitAtom` | 5 | `description`*, `category` | Description | rasgo aprendible del usuario; candidato para el perfilador |
| `gate` | `GateCriterion` | 5 | `criterion`*, `approval_condition`*, `rejection_action`* | Criterion, Approval Condition, Rejection Action | criterio post-redacción del gate |
| `boundary` | `CapabilityBoundary` | 2 | `restriction`*, `conditions`, `escalation` | Restriction, Conditions, Escalation | límite duro de lo que el agente puede hacer |
| `tool` | `ToolAtom` | 1 | `description`*, `parameters`* | Description, Parameters | declaración de una tool para el LLM |
| `style` | `StyleGuide` | 1 | `tone`*, `language_register`*, `phrase_preferences`, `length_guidelines` | Tone, Language Register, ... | estilo de redacción |
| `strategy` | `StrategyRule` | 1 | `goal`*, `approach`*, `priorities` | Goal, Approach, Priorities | estrategia conversacional |
| `self` | `SelfDeclaration` | 1 | `statement`* | Statement | quién es el agente |
| `fallback` | `FallbackRule` | 1 | `fallback_message`*, `conditions` | Fallback Message, Conditions | qué decir cuando no hay corpus |

Los cinco de abajo (`tool`, `style`, `strategy`, `self`, `fallback`) son
**singletons de configuración**: una KB = un negocio = uno de cada. Los seis
de arriba son **colecciones**.

---

## 4. Relaciones entre documentos

Hay dos familias de relación: **genéricas** (cualquier doc con cualquier
doc) y **tipadas** (declaradas por un modelo concreto, con semántica propia).

### 4.1 Genéricas

| Relación | Mecanismo | Aristas en KGDB | Lector hoy |
|---|---|---|---|
| comparte tag | `tags` | `doc → tag`, `tag → tag` (`semantic_parent`) | `docs_for_tag`, `siblings`, `steps_under` |
| jerarquía | `parent` | — | ninguno |
| ancla semántica | `semantic_anchors` | — | ninguno (y está vacío) |
| similitud | `embedding` | — | ninguno |

#### Namespaces de tags

Definidos en `knowledge/desk/atoms/tag-namespaces.yaml` vs. uso real en los
71 documentos:

| Namespace | Definido | Usado (docs) | Ejemplo | Nota |
|---|---|---|---|---|
| `system` | sí | 71 | `system:laboratorio-chile` | constante; no discrimina |
| `domain` | sí | 35 | `domain:seguridad.triage` | jerárquico por `.` |
| `conversation` | **no** | 31 | `conversation:steps.onboarding` | **el más importante, sin definir** |
| `topic` | sí | 6 | `topic:rules` | |
| `gate` | sí | 5 | `gate:corpus` | |
| `self` | **no** | 5 | `self:whoami` | |
| `user` | **no** | 5 | `user:trait` | |
| `channel` | **no** | 1 | | |
| `layer` | sí | 0 | | definido, sin uso |
| `source` | sí | 0 | | definido, sin uso (reflector debería usarlo) |

**Cuatro namespaces en uso no están definidos**, incluido `conversation`,
que es el eje del flujo. El archivo de namespaces describe otra KB (la de
`desk/`), no ésta.

### 4.2 Tipadas: el flujo conversacional

`ConversationStep` declara tres relaciones con semántica propia. KGDB las
convierte en aristas tipadas:

| Campo del step | Apunta a | Arista KGDB | Método lector |
|---|---|---|---|
| `allowed_transitions` | otros steps (por tag) | `REL_FLOWS_TO` | `get_next_transitions(node)` |
| `grounding_atoms` | ids de `domain`/`self`/... | `REL_GROUNDED_BY` | `get_grounding_atoms(node)` |
| `tool_ref` | id de `tool` | — | `get_tools_for_node(node)` |

Y el grafo declarado en los 11 steps, tal como está en los documentos:

```mermaid
flowchart LR
    saludo --> onboarding
    saludo --> registro_estado
    saludo --> journey_operativo
    saludo --> derivacion_medinfo
    onboarding --> registro_estado
    journey_operativo --> registro_estado
    journey_operativo --> despedida
    registro_estado --> evento_adverso
    registro_estado --> agendar_recordatorio
    registro_estado --> derivacion_medinfo
    agendar_recordatorio --> recompra
    recompra --> despedida
    evento_adverso --> despedida
    derivacion_medinfo --> revision_humana
    derivacion_medinfo --> despedida
    validacion_policy_gate --> revision_humana
    revision_humana --> despedida
    despedida:::terminal
    classDef terminal stroke-dasharray: 4 4
```

Es un flujo real, con entrada (`saludo`), salida (`despedida`, terminal) y
ramas de seguridad (`evento_adverso`, `derivacion_medinfo` →
`revision_humana`). `validacion_policy_gate` no tiene entrada declarada
desde ningún step: es el nodo al que el gate debería saltar, pero nadie
transiciona a él.

**Hoy — el bug de cableado:** el compilador no usa ninguna de estas
aristas. `_augment_from_kgdb` (`compiler.py:274-316`) llama a
`steps_under()` y expone como transiciones permitidas *todos los hermanos*,
y usa `docs_for_tag()` en vez de `get_grounding_atoms()`. Resultado: desde
`despedida` (terminal) el runtime cree que puede ir a cualquiera de los
otros 10 steps. El grafo declarado y sus lectores existen; falta llamarlos.

---

## 5. Documentos ↔ agentes

Cruce de los 11 tipos con los cuatro agentes del diseño (más perfilador y
reflector, que no son agentes de turno). **F** = contexto fijo, cargado al
arrancar; **D** = dinámico, seleccionado por turno.

| Tipo | Conversador | Ruteador de contexto | Orquestador | Gate | Perfilador | Reflector |
|---|---|---|---|---|---|---|
| `self`, `style`, `boundary` | **F** (persona) | | | | | |
| `strategy` | **F** | | | | | |
| `fallback` | **F** | | **F** (decide fallback) | | | |
| `domain` | D (lo que entrega el ruteador) | **D** busca | | | | escribe nuevos |
| `rule` | D | **D** busca | D (clasificación) | | | |
| `step` | D (instrucciones del step activo) | **D** step actual + grounding | **F** flow completo | | | |
| `tool` | | | **F** tools disponibles | | | |
| `gate` | | | | **F** | | |
| `trait` | D (perfil del usuario, vía SQL) | D | | | **F** candidatos | |

### 5.1 Quién los lee hoy (código)

| Tipo | Consumidor actual | Cómo |
|---|---|---|
| `domain`, `rule` | `ContextCompiler._find_atoms` (`compiler.py:73-74`) | **todos**, sin selección |
| `self`, `style`, `boundary` | `_extract_persona` (`compiler.py:190-226`) | singleton → `persona` |
| `strategy` | `_extract_strategy` (`:228`) | singleton |
| `fallback` | `_extract_fallback` (`:242`) | singleton |
| `tool` | `_find_tools` (`:249`) | todos → `function_declarations` |
| `step` | `_augment_from_kgdb` (`:274`) vía KGDB | step activo + hermanos (ver §4.2) |
| `trait` | `TraitExtractor` (`perfilador/extractor.py:75`, `reader.fetch("trait")`) | candidatos → LLM elige → SQL |
| `gate` | `Orchestrator._validate_response` (`orchestrator.py:277`) | lee los 5, decide con heurísticas de string |

La columna "Ruteador de contexto" de la tabla 5 está vacía en el código:
ese agente no existe (ver `AGENT-CONTRACTS.md` §2.2).

---

## 6. Documentos ↔ SQL

SQL no guarda conocimiento; guarda **estado por usuario** que *referencia*
conocimiento. Todas las junturas son **strings sin integridad referencial**:
SQL no sabe que el id existe en la KB, y renombrar un documento deja filas
colgando.

```mermaid
flowchart TB
    subgraph SQL["SQL (kb_agent/models_sql)"]
        users["users<br/>id, external_id, channel"]
        traits["user_traits<br/>user_id, trait_id, confidence, source"]
        state["session_state<br/>user_id, flow_node, flow_slots,<br/>active_domain, current_node, buffer"]
        hist["chat_history<br/>user_id, role, content, pii_scrubbed"]
        rec["recordatorios<br/>user_id, dia, hora, nombre"]
        res["reservas<br/>user_id, fecha, hora, personas"]
        users --> traits & state & hist & rec & res
    end

    subgraph KB["knowledge/atoms"]
        T["trait-*<br/>TraitAtom"]
        S["step-*<br/>ConversationStep"]
        TL["tool-*<br/>ToolAtom"]
        D["atom-* / rule-*<br/>Domain / Rule"]
    end

    traits -. "trait_id = TraitAtom.id" .-> T
    state -. "flow_node = tag conversation:steps.*" .-> S
    state -. "flow_slots ⊂ step.required_slots" .-> S
    rec -. "escrito por tool agendar_recordatorio<br/>(step.tool_ref → ToolAtom)" .-> TL
    res -. "escrito por tool crear_reserva" .-> TL
    hist -. "Reflector lee → genera<br/>(provenance source:reflector)" .-> D
```

| Columna SQL | Referencia en KB | Quién escribe | Quién lee | Validación |
|---|---|---|---|---|
| `user_traits.trait_id` | `TraitAtom.id` (`trait-antonia-*`) | perfilador (post-turno) | compilador → `persona`/perfil | ninguna |
| `session_state.flow_node` | tag `conversation:steps.<step>` | orquestador (post-turno) | compilador → step activo | `current_step in steps`, si no cae a onboarding |
| `session_state.flow_slots` | claves de `step.required_slots` | orquestador | compilador → `missing_slots` | ninguna |
| `session_state.active_domain` | valor de tag `domain:*` | orquestador | compilador → `scenario` (solo etiqueta) | ninguna |
| `recordatorios.*` / `reservas.*` | — (efecto de `ToolAtom`) | tool handler | nadie del runtime | — |
| `chat_history.*` | — | orquestador | **reflector** (batch, offline) | — |

Dos cosas que SQL **no** tiene y el diseño necesita:

- **Sesión / conversación**: `chat_history` es una lista plana por usuario.
  No hay `session_id`.
- **Rastro de turno**: qué documentos entraron al contexto, qué step estaba
  activo, qué decidió el gate. Se calcula en cada turno y se pierde.

Con eso, el vínculo documento ↔ turno (que es lo que haría auditable una
respuesta pasada) **no existe en SQL**; sólo existe en la respuesta HTTP
mientras dura.

---

## 7. Cómo se busca (los readers)

### SLDBReader — búsqueda por semántica

```python
reader.find("type.knowledge.domain")      # todos los DomainAtom
reader.find("conversation:steps.onboarding")  # docs con ese tag
reader.fetch("trait")                      # azúcar de find("type.knowledge.trait")
reader.find_fields(term)                   # también secciones y campos, no solo docs
reader.get_doc(doc_id)                     # campos resueltos de un doc
```

El eje `type.knowledge.<tipo>` sale del `semantics` de la clase, no de un
tag. Por eso `atom_type` es campo del modelo y no tag.

**Hoy:** estas funciones son internas. No están expuestas como tools al
LLM, así que ningún agente puede *buscar*; sólo el compilador *carga*.

### KGDBReader — grafo

Nodos: documentos y tags (`tag:<ns>:<valor>`). Aristas: `doc → tag`,
`tag → tag` (`semantic_parent`, desde `semantic_dag.yaml`), y las tipadas
del step (`REL_FLOWS_TO`, `REL_GROUNDED_BY`). Métodos: `steps_under`,
`docs_for_tag`, `siblings`, `get_next_transitions`, `get_grounding_atoms`,
`get_tools_for_node`.

---

## 8. Inconsistencias encontradas

Por orden de impacto sobre el comportamiento:

1. **Transiciones y grounding declarados pero no cableados** (§4.2). El
   flujo está bien modelado en la KB y KGDB lo lee; el compilador usa los
   métodos genéricos en vez de los tipados. Dos líneas.
2. **Sin selección de `domain`/`rule`** (§5.1). Se cargan los 43 en cada
   turno. Los embeddings que resolverían esto están poblados y sin lector.
3. **`semantic_anchors` vacío en 71/71.** O se puebla o se quita del modelo;
   como está, es una promesa falsa en el esquema.
4. **Namespaces de tags desincronizados** (§4.1): `conversation`, `self`,
   `user`, `channel` en uso sin definición; `layer`, `source` definidos sin
   uso. El archivo describe la KB de `desk/`, no ésta.
5. **Junturas SQL↔KB sin validación** (§6). Nada detecta un `trait_id` o
   `flow_node` huérfano.
6. **`validacion_policy_gate` es inalcanzable** en el grafo declarado
   (ningún step transiciona a él) y el gate real no navega a ningún step.
7. **`domain_ref` y `system:` constantes.** No discriminan nada mientras
   haya un solo negocio por KB; son ruido en cada documento.
8. **Registro con rutas de un worktree borrado** (§1.1).
9. **`parent` a medias** (23/71): la jerarquía `farmacovigilancia → {ea,
   gamp5, ime, meddra, triage}` existe pero nadie la recorre.

---

## 9. Cómo se verificó

- Campos por modelo: introspección de `model_fields` de las 11 clases en
  `kb_agent.models.knowledge`.
- Uso de campos y tags: parseo del frontmatter de los 71 `.md`.
- Transiciones declaradas: sección `## Allowed Transitions` de los 11
  `step-*.md`.
- Consumidores: `grep type.knowledge.<tipo>|fetch("<tipo>")` sobre
  `kb_agent/`, más lectura de `compiler.py`, `kgdb_reader.py`,
  `orchestrator.py`, `perfilador/extractor.py`.
- Namespaces: `knowledge/desk/atoms/tag-namespaces.yaml` vs. conteo real.
- SQL: `kb_agent/models_sql/*.py` y `PRAGMA table_info` sobre
  `runs/local-chat.sqlite`.
