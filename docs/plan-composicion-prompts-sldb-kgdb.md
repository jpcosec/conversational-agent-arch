# Plan — Composición de system prompts sobre SLDB + KGDB

Estado: propuesta acordada (2026-09-09). Reemplaza la idea anterior de un
spec YAML estilo wiki: **el spec ya existe** y es el grafo tipado de la KB
(RelationTypeDoc + RelationDoc en `knowledge_hcp/relations/`).

## Contexto

- Los agentes se construyen una vez en `Orchestrator.__init__` con
  `static_instruction` generado por las mismas `render_*` que sirve
  `/api/system-prompts`. Hay dos fuentes de render (la vista re-renderiza por
  su cuenta) → byte-exacto no está garantizado ni testeado.
- Composición actual: parcial. `AgentFraming`, `GateCriterion` y
  `ConversationStep` vienen de atoms SLDB **por escaneo de tipo**
  (`docs_by_type(...)`). La doctrina del ruteador (`_ROUTER_INSTRUCTION`,
  familias, motivos, regla de oro) vive hardcodeada en
  `kb_agent/agents/router.py`.
- La KB ya declara 3 RelationTypeDoc (`grounded_by`, `transitions_to`,
  `uses_tool`) y 49 RelationDoc que dicen qué atom interviene en qué step.
  El compilador no los usa.

## Principio (lectura sldb + kgdb + pron)

- SLDB es la capa de documentos: atoms + RelationDocs como Markdown, stores,
  indexado semántico.
- KGDB es la capa de grafo: los RelationTypeDoc son los verbos transitivos
  almacenados como documentos SLDB; los RelationDoc son instancias con
  `source_id` / `target_id` / `relation_type` y provenance. Referencias
  rotas se reportan como hallazgos (`graph missing`), nunca se silencian.
- pron es la capa de consulta sobre el mundo: nouns = direcciones sldb,
  verbos transitivos = RelationTypeDoc, writes = writes sldb.

Consecuencia: la composición de prompts es **traversal del grafo**, no
escaneo por tipo ni spec paralelo. La provenance sale gratis de las aristas.

## Paso 1 — Exactitud: la vista == el system real

1. Extraer un único builder en `kb_agent/agents/`:
   `build_agent_prompts(knowledge_ops) -> dict[rol, {static_instruction}]`
   para router, gate, orchestrator y conversador.
2. `Orchestrator.__init__` consume `static_instruction` de ese builder
   (hoy: `_load_agent_framing` + renders dispersos).
3. `/api/system-prompts` (`frontends/chat/app.py`) sirve **el mismo dict**,
   sin re-render propio.
4. Test de contrato: `GET /api/system-prompts` == `agente.static_instruction`
   byte a byte para los 4 roles.

Notas:
- El cuerpo dinámico por turno (`build_nl_prompt`: PASO ACTUAL, datos ya
  dados, historial) no es system instruction; el builder expone su
  **contrato** (secciones) para la vista, pero no se renderiza por turno ahí.
- `_load_agent_framing` queda como detalle interno del builder.

## Paso 2 — Composición como traversal del grafo

1. Nodos de agente en la KB: `agent:router`, `agent:gate`,
   `agent:orchestrator`, `agent:conversador` (los AgentFraming existentes
   proveen el texto; los nodos dan el ancla del grafo).
2. Nuevos RelationTypeDoc (mismo mecanismo que `grounded_by`):
   - `framed_by`: agente → AgentFraming.
   - `judged_by`: agent:gate → GateCriterion (hoy el gate escanea
     `gate_atoms`).
   - `orchestrates`: agent:orchestrator → ConversationStep.
   - `grounded_by` reutilizado para la doctrina: agent:router → atoms de
     doctrina (familias, motivos, regla de oro), que migran desde
     `_ROUTER_INSTRUCTION` (hardcodeado) a atoms familia self.
3. Migración de la doctrina del ruteador a atoms de la KB
   (`knowledge_hcp`): el código queda como fallback genérico, la KB como
   fuente de verdad del negocio.
4. El builder de prompts resuelve secciones **siguiendo aristas
   declaradas**, devolviendo secciones con metadata:
   `{title, text, atom_id, source_path, relation_id}`.
   Falta un atom referenciado = error (no drift silencioso).
5. Instancias RelationDoc nuevas en `knowledge_hcp/relations/`, trackeadas
   en el store SLDB como las 49 existentes.

## Paso 3 — Behaviour de la wiki sobre la vista y el ciclo

1. `/dev/prompts` materializa el traversal: cada bloque con
   `data-atom` / `data-source` / `data-relation`; click abre panel de
   origen (atom id, archivo, RelationDoc, provenance).
2. `digest` sha256 + `atom_count` por prompt de agente, persistidos
   (runtime state, no fuente): el diff delata drift de prompt.
3. Check de composición corrible en CI (junto a pytest):
   - aristas colgantes (source/target inexistente) = fallo,
   - atom referenciado por el builder inexistente = fallo,
   - tool declarada por la KB sin handler = fallo.
   Equivalente a `pron check` / `deskops graph missing` para este dominio.

## Orden de trabajo

Paso 1 primero (es pequeño y destraba tests de contrato), luego paso 2
(grafo + migración de doctrina), luego paso 3 (vista + checks). El paso 2
toca la ontología de la KB (nuevos RelationTypeDoc) — hacerlo como se hizo
con los 3 existentes: modelo + template + instancias + stores update.

## Archivos que cambian

- `kb_agent/agents/` — builder único + renders con metadata de secciones.
- `kb_agent/orchestrator.py` — init consume el builder.
- `frontends/chat/app.py` — `/api/system-prompts` sirve el dict del builder.
- `frontends/dev/prompts` (HTML/JS/CSS) — provenance UI.
- `knowledge_hcp/` — nodos de agente, RelationTypeDoc nuevos, RelationDoc
  nuevos, atoms de doctrina del ruteador.
- `tests/` — contrato byte-exacto, traversal con aristas faltantes, digest.

## Fuera de alcance (explícito)

- No cambiar el runtime del Conversador ni `build_nl_prompt` (solo exponer
  contrato).
- No mover la wiki de AntonIA: es referencia de behaviour, no código a
  copiar.
