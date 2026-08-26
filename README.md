# Conversational Agent Architecture

Agente conversacional multi-dominio con arquitectura de 4 motores cognitivos, almacenamiento híbrido (SQL + SLDB + KGDB), runtime sin hardcodes de negocio (`project.config.yaml` + KB) y una suite que incluye pruebas agente-vs-agente.

## Arquitectura

**4 motores cognitivos**
- **Conversador** — responde en NL, nunca alucina (fallback estricto ante contexto vacío)
- **Ontologizador** — compila contexto navegando SLDB + KGDB
- **Perfilador** — extrae traits del usuario de forma asíncrona (sin PII)
- **Reflector** — genera atoms nuevos desde el historial en batch

**Capas de datos**
- **SQL** — identidad, sesión, estado vivo, PII, historial, reservas
- **SLDB** — conocimiento semántico (atoms, facts, rules, tools, traits)
- **KGDB** — grafo de relaciones y flujo conversacional

## Estructura del repositorio

```
desk/                      # Workflow harness del proyecto (tasks, rituals, deskops)
  atoms/                   #   Átomos de arquitectura del agente runtime
  tasks/ rituals/ ...

knowledge/                 # Knowledge Base del agente (modelo de conocimiento)
  atoms/                   #   Taxonomía: domain, rule, tool, trait + tag-namespaces

tests/
  knowledge/               #   KB de prueba: Don Peppe (pizzería)
  knowledge_antonia/       #   KB de prueba: Antonia (programa de pacientes)
  unit/ integration/ e2e/ ui/   # suite (ver "Tests")

kb_agent/                  # Runtime del agente conversacional
frontends/                 # UIs estáticas + entrypoint HTTP
  chat/                    #   app.py (factory FastAPI) + server.py (entrypoint) + index.html
  flow_editor/             #   editor visual del grafo de ConversationStep
  profiling/               #   viewer de perfiles de usuario (traits)
  taxonomy/                #   explorador de la taxonomía de la KB
  viz/                     #   visualizador de diagramas (deskops/spec2viz)
project.config.yaml        # QUÉ negocio corre: KB, modelo, tools, server, marca
```

**Regla**: `desk/` es solo workflow. `knowledge/` es la KB reutilizable. `tests/knowledge*/` son KBs de prueba. Nada del negocio (nombres, paths, tools, modelo) vive en el código: todo sale de la KB o de `project.config.yaml`.

## Componentes

```
kb_agent/
├── agent.py                    # policy PURA de turno (decide_turn): tool_call | fallback | nl
├── llm.py                      # puertos Conversador/TraitMapper + implementación Gemini
├── orchestrator.py             # cablea SLDB + KGDB + SQL + LLM (inyectable) + tools
├── tools/                      # registry de handlers (declarados en project.config.yaml)
├── project_config.py           # carga project.config.yaml (+ overrides por env)
├── cli.py                      # CLI local
├── state_machine.py            # RouterStateMachine (ejecución técnica de turno)
├── ontologizador/
│   ├── sldb_reader.py          # lee SLDB via librería real
│   ├── kgdb_reader.py          # navega grafo KGDB
│   ├── compiler.py             # produce CompiledDocument
│   └── compiled_document.py
├── models_sql/                 # identity, session, reservas
├── perfilador/                 # listener + extractor async
├── reflector/                  # batch reader + atom generator
└── pii/scrubber.py             # enmascara PII en origen
```

## Uso

```bash
# chat local (negocio de project.config.yaml; requiere credenciales Gemini/Vertex en .env)
python -m kb_agent.cli

# servidor HTTP (chat UI, editor de flujo, taxonomía, perfilado, webhook Twilio)
python -m frontends.chat.server      # host/port desde project.config.yaml o HOST/PORT
```

Cambiar de negocio = editar `project.config.yaml` (`kb_root`, `model`, `tools`, marca) o usar
`PROJECT_CONFIG=/ruta/otro.yaml`. Los handlers de tools se declaran ahí como `modulo:funcion`.

## Tests

Cuatro capas, de más rápida a más cara. Solo `e2e` y `ui` necesitan algo externo.

| Capa | Qué prueba | Necesita | Comando |
|---|---|---|---|
| `tests/unit` | policy, compilador, state machine, modelos SQL, CLI knowledge, **orquestador completo con LLM fake** (puertos inyectados), harness de simulación | nada | `pytest tests/unit` |
| `tests/integration` | API FastAPI (chat, flow, profiles, **Twilio**), reflector cableado, CLI por subprocess, export de flujo | nada | `pytest tests/integration` |
| `tests/e2e` | Gemini real: smoke (NL cita la KB, perfilador aprende) + **simulación agente-vs-agente** | `.env` (Vertex ADC) | `pytest tests/e2e` |
| `tests/ui` | Playwright contra la app in-process (LLM fake) | Chromium | `pytest tests/ui` |

Marcadores: `llm` (se salta sin credenciales o con `SKIP_LLM_TESTS=1`), `simulation`, `ui`,
`known_gap` (defecto documentado del runtime; `xfail` **estricto**: al arreglarse, el test exige quitar la marca).
La suite nunca escribe en `runs/ui-chat.sqlite` ni en la KB real (`CHAT_DB` apunta a un sqlite temporal; `project_config` carga `test_kb_root`).

### Probar el agente conversacional con un agente conversacional

`tests/e2e/simulation/` enfrenta al runtime real (Gemini + SLDB + SQL + tools) con un **usuario simulado**
(otro LLM que interpreta una `Persona` con objetivo, datos privados y comportamiento), y evalúa la
transcripción con un **juez LLM** que recibe la KB compilada como única verdad. Por escenario:

1. `runner.run_conversation` conversa hasta que el usuario cumple su objetivo o se agotan los turnos.
2. `checks` deterministas sobre el runtime: tool ejecutada con qué args, filas en SQL, traits aprendidos
   y usados en el turno siguiente, ausencia de `tool_call`/`fallback`, largo de respuestas.
3. `Judge` evalúa criterios (`grounded` = ningún dato fuera de la KB, `in_character`, y criterios propios
   del escenario) con salida JSON tipada y evidencia textual.

Escenarios en `scenarios.py` (Don Peppe: consulta general, reserva completa, reserva paso a paso, fuera de
alcance, perfil vegetariano, regla de reservas, manipulación; Antonia: dosis doble, evento adverso,
recordatorio con tool inyectada). Las transcripciones quedan en `runs/simulation/<escenario>.json` y se
imprimen en el mensaje de fallo.

```bash
pytest tests/e2e/simulation -m simulation            # todos
pytest tests/e2e/simulation -k antonia               # una KB
pytest tests/unit/test_simulation_harness.py         # el harness en sí, sin red
```

## Principios de diseño

- Perfiles como subgrafos reutilizables (TraitAtoms universales; SQL mapea `user_id -> trait_ids`)
- KB multi-dominio: intercambiar atoms SLDB repurpone el bot
- El compilador navega el grafo, no filtra por tags planos
- La state machine técnica (ejecución) es distinta del flujo conversacional (semántico)

## Dependencias

- [sldb](https://github.com/jpcosec/sldb) — capa de documentos estructurados
- [kgdb](https://github.com/jpcosec/kgdb) — grafo de conocimiento
- Google Gemini (Vertex ADC)
