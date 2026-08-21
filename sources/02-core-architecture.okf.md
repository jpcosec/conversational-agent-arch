# ADK Core Architecture

type: architecture
topic: core-architecture
source: https://github.com/google/adk-python
source-docs: https://adk.dev/agents/

## Public API (top-level imports)

```python
from google.adk import Agent      # LlmAgent alias
from google.adk import Context    # Agent execution context
from google.adk import Event      # Event model
from google.adk import Runner     # Execution engine
from google.adk import Workflow   # Graph-based orchestration
```

## Agent types hierarchy

All agents extend `BaseAgent` (which extends `BaseNode` from workflow module).

| Agent type | Import path | Mode | Use case |
|------------|-------------|------|----------|
| **Agent** / **LlmAgent** | `google.adk.agents.LlmAgent` | single_turn, task, chat | Main LLM agent with tools, sub-agents |
| **LoopAgent** | `google.adk.agents.LoopAgent` | loop | Repeat until exit condition |
| **SequentialAgent** | `google.adk.agents.SequentialAgent` | sequential | Ordered chain of sub-agents |
| **ParallelAgent** | `google.adk.agents.ParallelAgent` | parallel | Fan-out sub-agents concurrently |
| **ManagedAgent** | `google.adk.agents.ManagedAgent` | managed | Agent backed by remote server |
| **Workflow** | `google.adk.Workflow` | graph | DAG-based orchestration of nodes |

## LlmAgent modes

### single_turn (default for workflow nodes)
- Stateless by default (`include_contents="none"`).
- Exposed as a **tool** to parent, not transfer target.
- Sub-branch isolation: parent can't see sub-agent internals.
- Can opt into history with `include_contents="default"`.

### task
- Runs until explicit `finish_task()` call.
- Supports multi-turn user interaction (pauses/resumes).
- Structured I/O via `input_schema`/`output_schema` (Pydantic models).
- Exposed as a tool; parent is suspended while task runs.
- Auto-validates output against schema, retry on failure.

### chat
- Full conversation history preserved.
- Supports direct transfer (`transfer_to_agent`).
- Peer-to-peer agent delegation.

## Context object

```python
class Context:
    state                    # dict with scoped keys (app:, user:, temp:)
    session                  # Current Session
    user_id / session_id     # Identifiers
    tool_context             # Tool execution context
    
    # Memory operations
    add_session_to_memory()
    search_memory(query)
    add_memory(memories)
    
    # Session operations
    append_event(event)
    get_session()
```

## Runner

```python
Runner(
    app_name: str,            # Application identifier
    agent: BaseAgent,          # Root agent
    session_service: BaseSessionService,
    memory_service: BaseMemoryService = None,
    artifact_service: BaseArtifactService = None,
    credential_service: BaseCredentialService = None,
    plugins: list[BasePlugin] = None,
    auto_create_session: bool = False,
    resumability_config: ResumabilityConfig = None,
)
```

- `runner.run_async(user_id, session_id, new_message)` returns async generator of Events.
- `runner.run(user_id, session_id, new_message)` synchronous wrapper.
- Manages full lifecycle: session load → agent execution → event append.

## Event model

```python
class Event:
    id: str                    # Unique event ID
    author: str                # Agent/user name
    content: types.Content     # Message content
    actions: EventActions      # Tool calls, state changes
    branch: str                # Branch path (e.g., "main.translator@1")
    partial: bool              # Streaming chunk flag
    is_final_response(): bool  # Last event in a turn
```

## Agent Config (no-code)

- JSON schema at: `src/google/adk/agents/config_schemas/AgentConfig.json`
- Supports defining agents declaratively without Python code.
- Integrates with Agent Studio for visual editing.

## Key architectural decisions

1. **Graph-native**: Workflow is first-class, not an add-on.
2. **Code-first, config-optional**: Python code is primary, JSON config secondary.
3. **Service abstraction layer**: Session, Memory, Artifact, Credential all swappable.
4. **Branch isolation**: Sub-agents run in branch hierarchy protecting parent context.
5. **Plugins for cross-cutting**: Tracing, logging, retry are plugins.