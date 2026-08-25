# Conversational Agent Architecture

Agente conversacional multi-dominio con arquitectura de 4 motores cognitivos, almacenamiento híbrido (SQL + SLDB + KGDB) y validación E2E real (sin mocks).

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

## Componentes

```
kb_agent/
├── agent.py                    # conversador + tool calling
├── orchestrator.py             # cablea SLDB + KGDB + SQL + Gemini
├── chat_local.py               # CLI local real
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
# chat local real (requiere credenciales Gemini/Vertex en .env)
python -m kb_agent.chat_local --kb .sldb_e2e_donpeppe --scenario pizzeria

# comandos: /exit, /scenario <dominio>, /reflect
```

## Tests

Validación real, sin mock/dummy/stub.

```bash
pytest tests/ --ignore=tests/e2e   # 44 unit
pytest tests/e2e/                   # 7 E2E reales (Gemini + SLDB + SQL + KGDB)
```

Todos los tests E2E pasan la **prueba de mutación**: fallan cuando se rompe lo que prueban.

## Principios de diseño

- Perfiles como subgrafos reutilizables (TraitAtoms universales; SQL mapea `user_id -> trait_ids`)
- KB multi-dominio: intercambiar atoms SLDB repurpone el bot
- El compilador navega el grafo, no filtra por tags planos
- La state machine técnica (ejecución) es distinta del flujo conversacional (semántico)

## Dependencias

- [sldb](https://github.com/jpcosec/sldb) — capa de documentos estructurados
- [kgdb](https://github.com/jpcosec/kgdb) — grafo de conocimiento
- Google Gemini (Vertex ADC)
