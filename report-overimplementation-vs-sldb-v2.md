# Reporte v2: qué reimplementa gemini_test que ya entregan sldb, kgdb y pron

Fecha: 2026-09-08. Verificado contra el código instalado (sldb y kgdb editables
desde `hum-ecosystem`, pron desde `legos/pron`, 49 tests de pron en verde) y
contra este repo en la rama `dev`.

## Estado al cierre (2026-09-08, rama dev)

Ejecutado, no solo diagnosticado:

- `kgdb init` sobre `knowledge/.sldb`; `transitions_to`, `grounded_by` y `uses_tool` como `RelationTypeDoc`, y el diagrama de Antonia como 53 `RelationDoc` (20 transiciones, 31 grounding, 2 tools). Mismos 12 nodos y 20 aristas que exportaba el flow editor antes; kgdb valida referencias colgantes en ensamblaje.
- `ConversationStep` sin `allowed_transitions`/`grounding_atoms`/`tool_ref`; `IndexProxies` sin `embedding`/`parent`/`semantic_anchors`. `kb_agent/knowledge/kgdb_reader.py` borrado; `kb_agent/knowledge/{world,flow,embedder}.py` son lo extra legítimo (política de arranque, vista del diagrama, adaptador fastembed).
- Embeddings en `knowledge/.pron/docs.<embedder>.json` (DocumentIndex de pron, por `hash_c`, fuera de git). Antonia indexada: 73/73 con vector.
- `KnowledgeOperations` sin subprocess a sldb, sin `index_hierarchy`, sin coseno propio; `promote`/`organize`/`propose` y el reflector escriben por `pron.Store`.
- pron ganó lo que faltaba (commits 230a99f, eb6cce1, bbecea5, d7f9002 en `legos/pron`): fix de paths relativos en `Store.create`, navegación genérica en `Graph`, `DocumentIndex`, `World.refresh_if_stale`.
- Suite: 310 passed, 5 skipped (Vitali ausente). Antes de empezar estaba en 38 errores por el fixture de Don Peppe borrado.
- Docs, specs spec2viz y atoms del desk actualizados (commits 7e1ff3a, 72d6a58, 63c8e93).

## Qué cambia respecto al v1

El v1 apuntaba al lugar equivocado. Decía que `knowledge_base/` era una CLI
redundante de ~600 líneas, que `desk/atoms/` no estaba trackeado y que
`demo_data.py` se reducía a tres líneas. Nada de eso se sostiene:
`knowledge_base/operations.py` tiene 1147 líneas y ya usa la librería de sldb,
`desk/atoms/` está trackeado en el `.sldb` raíz (45 `AtomDoc`), y la mitad de
`demo_data.py` es una máquina de estados con test Playwright.

Lo que sí sobra está en otra capa: **el diagrama de conversación, el grafo,
los embeddings y las escrituras al store**. Ahí gemini_test tiene su propia
versión, más frágil, de cosas que kgdb ya tipa y que sldb ya valida. pron
es un consumidor de las dos que muestra cómo usarlas bien; no es la
dependencia. Ese es el reporte.

## Lo que entregan hoy las tres piezas (verificado)

| pieza | qué da | dónde |
|---|---|---|
| sldb | store de documentos tipados con roundtrip, `find --where` (sí funciona `model <= ConversationStep`), export semántico `--format kgdb`, `stores update`, predicados con eje, cache de runtime | `hum-ecosystem/tools/sldb` |
| kgdb | **sustrato general de grafo**, no un accesorio de sldb: `KnowledgeNode` con identidad tipada y facetas (`semantics`, `ast`, `io_ports`, `compliance`, `git`, `source`), `StructuredQuery` (filtros por faceta, alcance por descendencia, filtro por tipo de relación y dirección), persistencia networkx, y varios ingests (`typed`, `authored_relations`, `sldb`). Encima, relaciones **tipadas** como documentos de sldb (`RelationTypeDoc`: `source_types`, `target_types`, `cardinality`, `axis`, `condition`; `RelationDoc` como arista autorada), `kgdb init` sobre un store, `ingest --store` que valida cada arista contra su tipo (endpoint inexistente = error), `edges`, `query` | `tools/kgdb/src/kgdb/{contracts,query,models,ingest,world.py}` |
| pron | un **consumidor** de las dos: `Store` (una sola puerta a sldb, lectura cacheada, evaluador `--where`, escrituras con roundtrip, guard por `hash_c`, undo), `Graph` (lee el grafo persistido de kgdb sin networkx, frescura por `hash_b`), `World.refresh()` (`stores update` + `build_typed_snapshot`, por librería), `Verbs` (transición = cambio de campo permitido si kgdb tiene la arista `transitions_to` y sldb cumple la condición), `Embedder`/`Matcher` (puerto, coseno, cache derivada fuera de git, fallback difflib), `ProjectionDoc`, `MoveDoc`. Todo eso son ~550 líneas sobre las APIs públicas de sldb y kgdb | `legos/pron/src/pron` |

Nota: el README de pron cita commits de sldb/kgdb (`e7a2c0c`, `cf0073d`,
`1c39c2b`, `1247139`) que no existen en el HEAD de `hum-ecosystem`. Da igual:
pron corre entero contra las versiones editables instaladas.

---

## Hallazgo 1 · El diagrama de conversación es texto libre parseado a mano

**Qué hay.** `ConversationStep.allowed_transitions` y `grounding_atoms` son
`str` libres (`kb_agent/models/knowledge/step.py:110-117`). El compilador los
parte por coma, descarta placeholders como "ninguno", busca la raíz del grafo
por diferencia de conjuntos y filtra referencias colgantes "defensivo ante
typos":

- `kb_agent/knowledge/compiler.py:723` `_split_declared_transitions`
- `kb_agent/knowledge/compiler.py:811` `_entry_step`
- `kb_agent/knowledge/compiler.py:837` `_resolve_kgdb_active_step`
- `kb_agent/knowledge/compiler.py:889` `_step_grounding_ids`
- `frontends/flow_editor/export_flow.py` (72 líneas, el mismo parseo para `/api/flow`)
- `kb_agent/agents/orchestrator_agent.py` `apply_transition_guard` (guardia en código contra ese mismo campo)

**Qué ya existe.** Exactamente esto es un `RelationDoc` de kgdb:
`source_id: ConversationStep:step-a`, `target_id: ConversationStep:step-b`,
`relation_type: transitions_to`, `condition: "..."`. El ingest tipado
(`kgdb/ingest/typed.py`) rechaza en ensamblaje una transición a un step que no
existe, verifica cardinalidad y clases. "¿Qué transiciones salen del step
activo?" es `kgdb edges --node <step>` filtrado por `transitions_to`, o una
`StructuredQuery` con `RelationFilter(relation_types=["transitions_to"],
direction="outgoing")`. Todo eso es kgdb. pron solo muestra la forma de
usarlo desde un runtime: `Verbs.transition` (`src/pron/verbs.py:164`) lee la
arista en kgdb y evalúa la condición con el `--where` de sldb sobre el estado
actual del sujeto, en 25 líneas. El spec 09a de pron declara un restaurante
con `Reservation.status` y transiciones `pending → confirmed` con condición
`party_size <= 8`; es el mismo problema que `leads`/`visitas` de este repo.

**Consecuencia.** `grounding_atoms` pasa a ser aristas `grounded_by`
(step → atom), `tool_ref` pasa a `uses_tool`, y `completion_condition`
(hoy texto para el LLM) puede ser un `--where` evaluable. El parseo del
compilador, `export_flow.py` y la validación de referencias colgantes
desaparecen. La guardia `apply_transition_guard` se queda, pero consulta el
grafo en vez de un string partido por comas.

**Costo.** ~250 líneas propias + una migración de 12 steps de Antonia a
`RelationDoc`. Es el cambio con más retorno del reporte.

---

## Hallazgo 2 · `KGDBReader` tiene código muerto y re-ingesta el grafo en cada llamada

**Código muerto.** `get_flow_node`, `get_next_transitions`,
`get_grounding_atoms`, `get_tools_for_node` y `find_nodes_by_type` de
`kb_agent/knowledge/kgdb_reader.py` leen aristas `flows_to`, `grounded_by`,
`uses_tool`. El ingest de kgdb nunca produce esas aristas (grep en
`tools/kgdb/src` devuelve cero). El propio compilador lo documenta en
`compiler.py:855`. Por eso `KnowledgeOperations.step_next`
(`operations.py:976`) devuelve **siempre** `allowed_transitions: []` y
`grounding_atoms: []`; el comando `step-next` de la CLI y `context()` sirven
datos vacíos. Los tests de `test_knowledge_cli.py:96-120` solo verifican que
`flow_node` no sea `None`, así que no lo detectan.

**Re-ingest por llamada.** `KnowledgeOperations._kgdb()`
(`operations.py:915`) construye un `KGDBReader.from_sldb` nuevo cada vez, y
`explore_multi` (la tool del `RouterAgent`) lo llama en cada consulta. Cada
llamada del ruteador vuelve a exportar el store entero y armar un `DiGraph`
en memoria. El orquestador sí guarda uno (`orchestrator.py:154`), pero
`explore_multi` no lo usa.

**Qué ya existe.** `kgdb ingest --store` (`build_typed_snapshot`) produce
el grafo una vez y lo persiste; `kgdb edges` y `kgdb query` lo consultan.
`root_tags`, `child_tags`, `docs_for_tag`, `sibling_docs` y `steps_under` de
`KGDBReader` son aristas `semantic_parent` y `tagged_as` leídas con
`edges_to`, o una `StructuredQuery` con `GraphScope(descendant_of=tag)`.
pron agrega encima lo que un runtime necesita y kgdb no decide: cuándo
refrescar (`World.refresh()` = `stores update` + ingest, por librería) y cómo
saber que el grafo está viejo (`Graph.is_fresh` compara los `hash_b` de los
modelos con los que se usaron al construirlo). Eso son 96 líneas en
`src/pron/graph.py` y 30 en `world.py`.

**Bonus que solo da kgdb.** `KnowledgeNode` tiene facetas (`source`, `git`,
`semantics`, `io_ports`) y hay más de un ingest. Los usuarios, traits y leads
que hoy viven en SQL y se cruzan a mano en `KnowledgeOperations.traits` y en
el compilador podrían entrar al mismo grafo como nodos con faceta `source`
por un ingest propio, y "qué atoms groundean el step activo para un usuario
con este trait" sería una sola `StructuredQuery`. No es parte de este
reporte, pero es la razón de fondo para depender de kgdb y no de un
envoltorio.

**Acción.** Borrar los cinco métodos muertos y `step_next` tal como está;
reemplazar `KGDBReader` por `pron.Graph` + `World.refresh()` llamado una vez
al arrancar y después de cada escritura. Se van ~296 líneas y un `nx.DiGraph`
por request.

---

## Hallazgo 3 · Los embeddings viven en el frontmatter y hoy no hay ninguno

**Qué hay.** `index_embeddings` (`operations.py:336`) escribe el vector de
768 floats al frontmatter de cada atom (`operations.py:384`), re-renderiza el
markdown y corre `sldb stores update` por subprocess. El template de cada
modelo reserva `embedding: ⸢optrev•embedding⸥` (`step.py:45`). Encima hay
`_cosine_sim`, `semantic_search`, `_fuzzy_search` con stopwords en español y
`explore_multi` (`operations.py:700-915`).

**Estado real.** De los 75 atoms de `knowledge/atoms/`, **cero** tienen
vector (`grep "^embedding: \["` devuelve 0). El retrieval semántico de
Antonia está degradado a fuzzy literal hoy, igual que lo estuvo Vitali. El
warning de `semantic_search` lo dice una vez por instancia y nadie lo lee.
El modelo `jina-embeddings-v2-base-es` está descargado en
`knowledge/.embedding_cache` (615 MB) pero nunca se corrió el índice.

**Por qué el diseño es el problema.** Meter el vector en el `.md` cambia
`hash_c` de todos los documentos cada vez que se re-indexa, ensucia el diff
de git, y obliga a re-render + `stores update` (subprocess) por atom. El spec
11 §2 de pron decidió lo contrario: los vectores van a un archivo derivado
fuera de git, nombrado por el hash de lo que embebe, invalidado cuando ese
hash cambia. `pron.embedder.Matcher` ya lo hace: `Embedder` es un `Protocol`
de dos métodos, la cache es un JSON en `.pron/`, y sin embedder cae a
difflib avisándolo en la traza.

**Diferencia que se conserva.** pron embebe el léxico (motivos de campos y
alias), no los documentos. gemini_test necesita embeber documentos para el
top-k del ruteador. Se trae el puerto, la cache y el fallback; el índice de
documentos se escribe con esa misma cache, keyed por `hash_c`.

**Acción.** Sacar `embedding` y `parent` de los templates; reemplazar
`index_embeddings`/`_cosine_sim`/`_embedder` por `Matcher` con un adaptador
fastembed; dejar `_fuzzy_search` como fallback o usar difflib de pron. Se van
~200 líneas y el frontmatter vuelve a ser contenido.

---

## Hallazgo 4 · Tres caminos distintos para escribir en el store

**Qué hay.**

- `KnowledgeOperations.propose` (`operations.py:1114`): renderiza markdown a
  mano con `render_model_markdown`, calcula ruta con `derive_path`, escribe el
  archivo, invalida cache. No trackea.
- `kb_agent/reflector/generator.py`: importa `track_document`,
  `validate_model_input_roundtrip` y `subprocess` directamente.
- `_run_sldb` (`operations.py:597`): subprocess al CLI para `docs track`,
  `docs untrack`, `stores update`, dentro de `index_embeddings` y
  `organize`.

Ninguno verifica `hash_c` antes de escribir, ninguno registra el valor
anterior, ninguno puede deshacer.

**Qué ya existe.** `pron.Store` (`src/pron/store.py`, 221 líneas) es una sola
puerta: `docs()` cacheado sobre `load_runtime_documents`, `find(scope,
where)`, `matches(model, name, where, payload)` con el evaluador `--where` de
sldb sobre un payload todavía no guardado, `schema(model)`, `hash_c`, y
`create`/`change`/`add`/`remove`/`clean`/`forget` con roundtrip, todo por
librería. `pron.Kernel` agrega guard por `hash_c`, dry-run y `undo`. El spec
04 lo fija como invariante: "cada verbo de acción es una llamada a la
librería de sldb, nunca un subproceso al CLI".

**Acción.** `propose` y el reflector escriben a través de `Store.create`;
`_run_sldb` desaparece. `organize` (mover archivos según tags) se queda porque
no es una escritura de sldb, pero retrackea vía `Store`.

---

## Hallazgo 5 · Jerarquía y taxonomía calculadas a mano sobre archivos de sldb

- `index_hierarchy` (`operations.py:447-520`) abre
  `.sldb/runtime/semantic_dag.yaml`, que es un archivo que sldb genera, y le
  agrega `parents` a mano. `stores update` lo regenera y las ediciones se
  pierden o se duplican según el orden.
- `/api/taxonomy` (`frontends/chat/app.py:498`) tiene un `MODEL_MAP` de 11
  entradas que dice a qué familia pertenece cada modelo. Eso ya está en
  `__family__` de cada modelo y en las aristas `has_model` / `extends` /
  `tagged_as` / `semantic_parent` del grafo tipado de kgdb.

**Acción.** Borrar `index_hierarchy`; `/api/taxonomy` recorre `Graph` o
llama `sldb ast show --format json`.

---

## Hallazgo 6 · Permisos y guardas en código en vez de declarados

**Qué hay.** `apply_security_floor` (`kb_agent/agents/router.py`) fuerza en
código que las `RuleAtom` con `conversation:security` entren siempre al
bundle. `apply_transition_guard` fuerza que `step_target` esté en
`allowed_transitions`. `MODEL_MAP` en el compilador decide qué campo de qué
modelo va a qué sección del prompt. Todo esto es correcto como guardia dura
(un LLM no es garantía), pero cada regla nueva es un `if`.

**Qué ya existe.** `ProjectionDoc` (`src/pron/models/projection.py`) declara
qué modelos, relaciones (con modo `read` o `read and assert`) y acciones
puede nombrar una sesión; `Kernel.allowed(verb)` y `Verbs.transition` son las
guardias, y leen el documento. Una proyección por agente (ruteador,
conversador, gate) reemplaza los `if` por documentos del store, y la
"regla de oro del ruteador" se vuelve una lista en `models`.

**Acción.** Segunda fase, después de los hallazgos 1 y 2. No es urgente pero
es donde el diseño "nada del negocio vive en código" de este repo todavía no
se cumple.

---

## Hallazgo 7 · Extracción determinista duplicada (menor)

`kb_agent/lead_slots.py` (125 líneas: email, teléfono, día, hora, modalidad)
y `frontends/chat/demo_data.py:638-700` (`DAY_RE`, `HOUR_RE`,
`extract_slots`) hacen lo mismo dos veces. pron tiene `surface/dates.py` y
`surface/tokens.py`, pero su léxico es inglés por decisión del spec 11 §0.
Unificar las dos copias del repo en una sí; traer la de pron todavía no.

---

## Hallazgo 8 · Ledger (anotar, no migrar)

`Turns` + `ChatHistory` + `state_trace` en SQL cumplen el rol del `MoveDoc`
de pron: qué entró, qué se leyó, qué se escribió, con qué motivo. El canal
es WhatsApp con PII scrubbeada y el ledger en SQL es la decisión correcta
para eso. Lo único que vale la pena copiar es el contrato del `record`
(interpretación, consultas exactas, escrituras con antes/después) para que
"¿por qué dijiste eso?" se conteste desde el turno y no desde logs.

---

## Lo que sobrevive del v1

- `knowledge_base/cli.py` + `__main__.py` (~125 líneas): prescindibles, todo
  se hace con `sldb`/`kgdb`/`pron` CLI. `step-next` además miente (hallazgo 2).
- `frontends/chat/demo_data.py`: las primeras 535 líneas de datos pueden ser
  documentos trackeados; la máquina de estados demo (360 líneas) se queda.
- Dos stores distintos (`knowledge/.sldb` de Antonia con modelos
  `kb_agent.models.knowledge`, `.sldb` raíz del desk con modelos `deskops`).
  No es un error, pero cualquier reporte que mezcle los dos se equivoca.
- `knowledge/.sldb/runtime/cache/` aparece sin trackear; agregarlo a
  `.gitignore` junto a las demás rutas de runtime.

## Lo que NO se trae de pron

- **La superficie SHRDLU** (`surface/`, `resolve.py`, `dialogue.py`,
  `session.py`: ~1600 líneas). En gemini_test el parser es el LLM; pron
  parsea oraciones sin LLM. Lo que sí se puede considerar más adelante es
  que el `OrchestratorAgent` ejecute transiciones y escrituras a través de
  `Kernel`/`Verbs` en vez de tools ad hoc, pero eso es un rediseño, no una
  limpieza.
- **El léxico en inglés** y los `AnchorDoc`. La KB de Antonia está en
  español y el LLM no necesita alias.
- **kinesis** (`MachineDoc`/`StateDoc`/`TransitionDoc` para
  `RouterStateMachine`). Existe y encaja, pero el router de 260 líneas
  funciona y tiene 328 líneas de tests; no es la prioridad.

## Orden de adopción

La dependencia es **kgdb + sldb**. De pron se copian tres archivos como
referencia de cómo usarlos desde un runtime (`store.py`, `graph.py`, el
`refresh` de `world.py`, y `embedder.py`), citando el commit de origen; no
se agrega pron como dependencia editable.

1. **`kgdb init` sobre `knowledge/.sldb`** y declarar `transitions_to`,
   `grounded_by`, `uses_tool` como `RelationTypeDoc` con `source_types`
   `ConversationStep`. Migrar los 12 steps de Antonia a `RelationDoc`
   (script de una vez, lee los campos libres actuales). Dejar
   `allowed_transitions`/`grounding_atoms` vacíos hasta borrarlos del
   modelo.
2. **`build_typed_snapshot` + grafo persistido** en el orquestador: un
   refresh al arrancar y tras cada escritura; `KGDBReader` se borra; el
   compilador lee transiciones y grounding con `edges_from` (copiado de
   `pron/graph.py`) o `kgdb.query.execute_query`.
3. **Una sola puerta al store** (copia de `pron/store.py`): `_find_records`,
   `_read_doc`, `_run_sldb`, `propose` y las escrituras del reflector pasan
   por ahí.
4. **`Matcher`** (copia de `pron/embedder.py`) con adaptador fastembed y cache derivada por
   `hash_c`; sacar `embedding` y `parent` de los templates; correr el índice
   de Antonia (hoy está en cero).
5. Borrar `knowledge_base/cli.py`, `index_hierarchy`, `export_flow.py`;
   `/api/flow` y `/api/taxonomy` leen el grafo.
6. (Después) `ProjectionDoc` por agente; `completion_condition` como
   `--where`.

Cada paso deja el runtime funcionando y los tests e2e pasando; 1 y 2 son los
que sacan bugs reales, 3 y 4 sacan código.

## Cuantitativo

| componente | líneas | qué lo reemplaza | acción |
|---|---|---|---|
| parseo del diagrama en `compiler.py` + `export_flow.py` | ~250 | `RelationDoc` + `kgdb ingest` + `kgdb edges` | migrar y borrar |
| `kgdb_reader.py` (5 métodos muertos + navegación por tags + re-ingest) | 296 | grafo persistido de kgdb + `execute_query` | borrar |
| `step_next` / `context` en `operations.py` | ~60 | devuelven vacío hoy | borrar |
| embeddings en frontmatter + coseno + `_embedder` | ~200 | `Matcher` (copia de pron) + cache derivada | reemplazar |
| `_run_sldb`, `propose`, escrituras del reflector | ~120 | una puerta al store (copia de `pron/store.py`) | reemplazar |
| `index_hierarchy` + `/api/taxonomy` `MODEL_MAP` | ~110 | grafo tipado / `ast show` | borrar |
| `knowledge_base/cli.py` + `__main__.py` | ~125 | CLIs de sldb/kgdb/pron | borrar |
| **total** | **~1.150** | | |

Lo que queda de `knowledge_base/operations.py` después de esto es
`semantic_search`/`explore_multi` (sobre `Matcher`), `traits` (cruce con
SQL), `organize`/`promote` (mover archivos) y `self_context`. Eso sí es
lógica del negocio y no está en ninguna de las tres librerías.

## Riesgos

- pron es v2 de este mes y cambia a su ritmo; por eso se copian sus tres
  archivos de infraestructura y no se depende de él. kgdb y sldb ya son
  dependencias del repo (el reflector y `KnowledgeOperations` los importan),
  así que no entra ninguna dependencia nueva.
- La migración de steps a `RelationDoc` toca la KB de Antonia, que está en
  producción en Modal desde el 27/08. Se hace en rama, se valida con los e2e
  de simulación, y se despliega junto con el runtime que la lee.
- El índice de embeddings hay que correrlo de verdad después del paso 4;
  hoy el retrieval semántico no existe en ninguna KB del repo.
