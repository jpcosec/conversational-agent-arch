# ADK SDK Packages

type: reference
topic: sdk-packages
source: https://adk.dev/

## Official ADK SDK repos

| Language | PyPI/NPM | Version | Stars | Repo |
|----------|----------|---------|-------|------|
| Python | google-adk | 2.7.1 | 21.2k | https://github.com/google/adk-python |
| TypeScript | @google/adk | 1.6.0 | 1.4k | https://github.com/google/adk-js |
| Go | - | - | - | https://github.com/google/adk-go |
| Java | - | - | - | https://github.com/google/adk-java |
| Kotlin | - | - | - | https://github.com/google/adk-kotlin |

## Key facts

- ADK 2.0 introduced **breaking changes** from 1.x (agent API, event model, session schema).
- Python version is the most mature (21k stars, bi-weekly releases).
- JS version is at 1.6.0 — significativamente detrás de Python.
- Go/Java/Kotlin repos existen pero con menos tracción.
- Samples repo: https://github.com/google/adk-samples (10k stars, same license).

## Python ADK structure

```
src/google/adk/
├── __init__.py        # Public API: Agent, Context, Event, Runner, Workflow
├── agents/            # Agent types, configs, context
├── workflow/          # Graph-based orchestration engine
├── runners.py         # Runner execution engine
├── memory/            # Memory service interface + implementations
├── sessions/          # Session service interface + implementations
├── tools/             # All tool types (MCP, OpenAPI, function, etc.)
├── models/            # LLM connections (Gemini, Anthropic, LiteLLM, etc.)
├── evaluation/        # Evaluation framework
├── optimization/      # Agent optimizer
├── cli/               # CLI tooling and dev UI
├── apps/              # App container
├── auth/              # Authentication framework
├── artifacts/         # Artifact services (file, GCS, in-memory)
├── plugins/           # Plugin system
├── code_executors/    # Sandboxed code execution
├── flows/             # LLM flow pipeline
├── integrations/      # Google Cloud integrations
├── skills/            # Skill management
├── planners/          # Planning strategies
├── events/            # Event model
├── labs/              # Experimental (OpenAI compat, antigravity)
├── telemetry/         # OpenTelemetry tracing
└── utils/             # Utilities
```

## ADK Docs site

- Main: https://adk.dev/
- API Reference: https://adk.dev/api-reference/
- Sitemap covers: agents, models, tools, workflows, memory, sessions, apps, callbacks, evaluation, a2a

## SDK installation

```bash
pip install google-adk          # Stable, Python 3.10+
pip install "google-adk[extensions]"  # With optional integrations
pip install "google-adk[gcp]"        # With GCP integrations
```

## Version compatibility

- ADK 2.0 sessions readable by ADK 1.28+ (extra fields ignored).
- Incompatible with ADK 1.x < 1.28.
- Release cadence: roughly bi-weekly for Python.