# CLI, UI, and Deployment

type: reference
topic: cli-deployment
source: https://github.com/google/adk-python/tree/main/src/google/adk/cli

## CLI commands

```bash
# Run agent interactively
adk run path/to/my_agent

# Launch web UI for dev/testing
adk web path/to/agents_dir

# Evaluate agent
adk eval agent_dir/ eval_set.json

# Create new agent project
adk create agent_name

# Deploy to Vertex AI
adk deploy agent_dir

# Run agent as API server
adk api_server agent_dir
```

## Developer Web UI

- Built-in dev UI served by `adk web`.
- Supports multi-agent directories.
- Real-time chat with agent.
- Graph visualization of workflow structure.
- Execution tracing and debugging.
- Based on SPA served from `cli/browser/` (pre-built chunks).

## API Server

```python
from google.adk.cli.api_server import start_server
# REST API for agent communication
```

- FastAPI-based.
- Supports WebSocket for bidirectional streaming.
- Configurable authentication.

## Deployment

### Vertex AI Agent Engine (primary path)

```bash
adk deploy agent_dir --project=my-project --location=us-central1
```

- Creates a reasoning engine resource.
- Managed runtime with sub-second cold starts.
- Memory Bank integration.
- Agent Identity (crypto ID).
- Agent Sandbox for code execution.
- Auto-scaling.

### Cloud Run

- Containerize agent with Docker.
- Deploy to Cloud Run.
- Use `ADK_WEB_SERVER_URL` and `ADK_API_SERVER` env vars.

### Self-hosted

- Plain asyncio runner in any Python process.
- `grpc` and `asyncio` based runners available.

## Config files

Agent directory structure:
```
my_agent/
├── agent.py            # Agent definition (code-first)
├── agent.yaml          # Agent definition (config-only)
└── .env                # Environment variables
```

- `agent.yaml` uses AgentConfig JSON schema for no-code agents.
- Can mix yaml + Python (config-optional philosophy).
- Sub-agents can be in separate directories/`__init__.py` files.

## Agent Identity (GCP)

- Crypto ID per agent via `integrations.agent_identity`.
- OAuth2 + IAM based authentication.
- GCP Auth Provider for Vertex AI.
- Mapped to authorized policies for audit trail.

## Recording and Replay

- `adk record` / `adk test` for conformance testing.
- Recordings plugin for capturing interactions.
- Replay plugin for deterministic replay testing.