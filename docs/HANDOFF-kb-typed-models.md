# Handoff — KB tipada + rediseño de agentes que razonan

Documento para retomar el trabajo con contexto nuevo.
Rama: `worktree/kb` · worktree: `/home/jp/proyectos/_worktrees/gemini_test-kb`

---

## 1. El problema de fondo (por qué existe este trabajo)

Hay un **gap conceptual grande** entre lo implementado y lo que debe ser.

Los agentes se implementaron tratando a **SLDB / KGDB / SQL como si fueran el
razonamiento**. Son herramientas de acceso e indexado, no razonan. El
razonamiento lo hacen los **agentes**.

Evidencia (revisada a fondo en el código fuente de los repos):

- **KGDB** README literal: *"KGDB is intentionally dumb. It stores and traverses
  graph facts; it does not decide whether SLDB's semantic interpretation is
  correct."* El grafo real solo tiene 4 relaciones: `has_model`, `has_document`,
  `tagged_as`, `semantic_parent`. Las relaciones `flows_to`, `grounded_by`,
  `uses_tool` que declara `kgdb_reader.py` **no existen** en el export.
- **SLDB** `find(term)` es matching de strings (literal/fuzzy/regex) sobre tags,
  no ranking semántico. El "semantic_dag" es solo jerarquía de tags padre/hijo.
- **SQL** guarda paciente + estado (traits, eventos). No razona.

Consecuencia: `ContextCompiler` usa `find("atom_type:domain")` como si fuera
selección inteligente, pero es solo un filtro de tag que **trae todo**. No razona
qué fichas sirven para el turno.

---

## 2. Modelo correcto (4 agentes que razonan)

| Agente | Rol | Herramientas (deterministas) |
|---|---|---|
| **Conversador** | Renderiza NL | — |
| **Orquestador** | Coordina, llama tools, actualiza contexto, **avanza steps** | tools, estado SQL |
| **Contexto** | **Razona** qué fichas seleccionar según parámetros del orquestador | SLDB/KGDB |
| **Reflector** | Captura casos especiales, loggea la conversación | SQL/SLDB |

SLDB/KGDB indexan y dan acceso a los átomos. SQL guarda paciente y estado
(traits, eventos) que luego se usa para recuperar cosas. **Ninguna de estas
herramientas deterministas reemplaza el razonamiento.**

Estado actual del código vs. objetivo:

| Agente | Debería | Está implementado como |
|---|---|---|
| Conversador | LLM que renderiza | ✅ `GeminiConversador` (correcto) |
| Orquestador | agente que **razona** el flujo | ❌ `Orchestrator` + `decide_turn` (determinista) |
| Contexto | agente que **razona** qué seleccionar | ❌ `ContextCompiler` trae todo por tipo |
| Reflector | captura casos + log | ⚠️ `ReflectorAtomGenerator` (batch de patrones) |

---

## 3. Lo que se hizo en esta sesión (rama worktree/kb)

### 3.1 Commit previo (c228a9d — no mío)
Introdujo **modelos SLDB tipados por tipo de átomo** en
`kb_agent/models/knowledge/` (10 modelos `StructuredNLDoc`):

| Modelo | atom_type | Campos propios |
|---|---|---|
| `DomainAtom` | domain | answer, domain_ref |
| `RuleAtom` | rule | answer, conditions, applies_to |
| `ToolAtom` | tool | description, parameters (JSON schema) |
| `TraitAtom` | trait | description, category (sin answer) |
| `ConversationStep` | step | instructions, required_slots, allowed_transitions, grounding_atoms, completion_condition |
| `SelfDeclaration` | self | statement |
| `StyleGuide` | style | tone, language_register, phrase_preferences, length_guidelines |
| `CapabilityBoundary` | boundary | restriction, conditions, escalation |
| `StrategyRule` | strategy | goal, approach, priorities |
| `FallbackRule` | fallback | fallback_message, conditions |

Guía: `knowledge/modelation-guide.md`. Anti-patrón clave declarado ahí:
**"no poner `atom_type` como tag en vez de campo — el Ontologizador filtra por
modelo, no por tag"**. La selección nueva es por `type.knowledge.<tipo>`
(derivado de `__semantics__`), no por `atom_type:<tipo>` como tag.

También creó dos KBs:
- `tests/knowledge_antonia/` — KB real tipada: **Antonia, PSP Selfix**
  (acompañamiento farmacéutico / adherencia a semaglutida). Caso serio con
  `CapabilityBoundary` clínicos absolutos, anti-alucinación, farmacovigilancia.
- `tests/knowledge/` — KB de prueba (Don Peppe) que **quedó en AtomDoc viejo**.

### 3.2 Este commit (migración de Don Peppe — mío)
Migré `tests/knowledge/` (Don Peppe) de `AtomDoc` genérico → 10 modelos tipados,
copiando la estructura de antonia. 7 átomos viejos → 15 átomos tipados.

Detalle en `docs/CHANGELOG-donpeppe-typed.md`.

**⚠️ NOTA IMPORTANTE**: el usuario señaló que **esto no era exactamente lo que
había pedido**. Se adelantó el trabajo e **inventé contenido nuevo** (ubicación,
promos, fallback/strategy/steps completos) en vez de solo migrar la forma de los
7 átomos existentes. Antes de continuar, **confirmar con el usuario** si:
  - (a) mantener la KB expandida como quedó, o
  - (b) revertir a solo los 7 átomos originales migrados a formato tipado sin
        inventar facts nuevos.

---

## 4. Diagnóstico técnico: el compilador se ROMPE con la KB tipada

Verificado ejecutando el reader contra antonia:

```
find("atom_type:domain")     → []   (vacío: atom_type ya no es tag)
find("type.knowledge.domain") → [4 docs]  (eje nuevo, funciona)
```

`ContextCompiler` entero selecciona por `atom_type:*` como tag → con KB tipada
da `is_empty=True` siempre → todo cae a fallback.

### Cambios mínimos para compatibilizar el compilador
1. `_find_atoms`: seleccionar por `type.knowledge.<tipo>`, no `atom_type:<tipo>`.
2. `_find_tools`: idem `type.knowledge.tool`.
3. Persona/estilo/límites: leer de modelos `SelfDeclaration.statement` /
   `StyleGuide.*` / `CapabilityBoundary.*`, no del `answer` con tag `self:*`.
4. `ConversationStep`: usar sus campos tipados (`allowed_transitions`,
   `grounding_atoms`, `required_slots`, `completion_condition`) en vez de derivar
   todo del KGDB tag-céntrico.

---

## 5. Trabajo en curso paralelo: CLI sobre knowledge

Apareció un paquete `knowledge_base/` (NO trackeado, de otro contexto/sesión):
`cli.py`, `operations.py`, `parser.py`. Es el inicio del **CLI sobre knowledge**
que el usuario quería exponer después de la migración.

Subcomandos previstos (de su docstring):
```
python -m knowledge_base --kb <path> explore <consulta>
python -m knowledge_base --kb <path> show <atom_id>
python -m knowledge_base --kb <path> step next --user <id>
python -m knowledge_base --kb <path> traits --user <id>
python -m knowledge_base --kb <path> self
python -m knowledge_base --kb <path> context --user <id>
python -m knowledge_base --kb <path> propose --model <m> --body <yaml>
```

Este paquete **no se incluyó en el commit de la KB** (es trabajo aparte, sin
terminar). Revisar/continuar por separado.

---

## 6. Próximos pasos sugeridos (en orden)

1. **Confirmar con el usuario** el alcance de la KB de Don Peppe (§3.2 nota).
2. **Arreglar el compilador** para la KB tipada (§4). Sin esto, antonia no corre
   y Don Peppe tipado tampoco compilaría.
3. **Unificar convención**: decidir si Don Peppe y antonia comparten selección
   por `type.knowledge.*` (ya lo hacen tras la migración).
4. **Terminar el CLI `knowledge_base/`** (§5).
5. **El salto grande**: convertir Contexto y Orquestador de deterministas a
   **agentes que razonan** sobre los modelos tipados (§2). Esto es lo central del
   rediseño; la taxonomía tipada es el sustrato, pero el razonamiento aún no
   existe.

---

## 7. Archivos y ubicaciones clave

- KBs: `tests/knowledge/` (Don Peppe), `tests/knowledge_antonia/` (Antonia)
- Modelos tipados: `kb_agent/models/knowledge/*.py`
- Guía de modelación: `knowledge/modelation-guide.md`
- Compilador (a arreglar): `kb_agent/ontologizador/compiler.py`
- Readers: `kb_agent/ontologizador/sldb_reader.py`, `kgdb_reader.py`
- Orquestador: `kb_agent/orchestrator.py` (GeminiConversador, GeminiTraitMapper, decide_turn)
- CLI en curso: `knowledge_base/` (untracked)

### Comandos SLDB útiles
```bash
# reindexar tras cambios en átomos
cd tests/knowledge && sldb stores update --store .sldb --pythonpath ../..
sldb stores check --store .sldb

# trackear un átomo con su modelo
sldb docs track atoms/<archivo>.md --model <Modelo> --store .sldb --pythonpath ../..

# selección por tipo (nuevo eje)
python3 -c "from kb_agent.ontologizador.sldb_reader import SLDBReader; \
  r=SLDBReader(kb_root='tests/knowledge', store_name='.sldb'); \
  print([x['id'] for x in r.find('type.knowledge.domain')])"
```
