# Memory and Sessions

type: architecture
topic: memory-sessions
source: https://github.com/google/adk-python/tree/main/docs/guides/memory
source-sessions: https://github.com/google/adk-python/tree/main/docs/guides/sessions

## Session Service

Session = conversation record with event history + state dict.

### Interface: BaseSessionService

```python
class BaseSessionService:
    async create_session(app_name, user_id, session_id=None, state={})
    async get_session(app_name, user_id, session_id, config=GetSessionConfig)
    async list_sessions(app_name, user_id)
    async delete_session(app_name, user_id, session_id)
    async append_event(session, event)       # Concrete in base class
```

### Built-in implementations

| Service | Import | When to use |
|---------|--------|-------------|
| InMemorySessionService | `google.adk.sessions` | Dev/testing only |
| DatabaseSessionService | `google.adk.sessions` | Production, any SQLAlchemy DB |
| VertexAiSessionService | `google.adk.sessions` | Vertex AI Agent Engine deploy |
| SqliteSessionService | `google.adk.sessions.sqlite_session_service` | Local dev (used by CLI) |

### State scoping

State keys have prefixes for lifetime control:

| Prefix | Constant | Scope |
|--------|----------|-------|
| (none) | - | This session only |
| `app:` | `State.APP_PREFIX` | Every session of the app |
| `user:` | `State.USER_PREFIX` | Every session of this user |
| `temp:` | `State.TEMP_PREFIX` | Current invocation only, not persisted |

### GetSessionConfig

```python
GetSessionConfig(
    num_recent_events=20,    # Bounded history load
    after_timestamp=...,     # Or cut by time
)
```

---

## Memory Service

For cross-session recall. Entirely opt-in.

### Interface: BaseMemoryService

```python
class BaseMemoryService:
    async add_session_to_memory(session)           # Required
    async search_memory(app_name, user_id, query)  # Required
    async add_events_to_memory(app_name, user_id, events, ...)  # Optional
    async add_memory(app_name, user_id, memories, ...)          # Optional
```

### Built-in implementations

| Service | Import | Retrieval type | Use case |
|---------|--------|----------------|----------|
| InMemoryMemoryService | `google.adk.memory` | Keyword match | Prototyping |
| VertexAiMemoryBankService | `google.adk.memory` | Semantic | Production (GCP) |
| VertexAiRagMemoryService | `google.adk.memory` | RAG corpus | RAG workflows |

### Memory tools (ready-made instances)

```python
from google.adk.tools import load_memory, preload_memory

# load_memory: model-driven, costs a tool call, only when needed
# preload_memory: automatic, runs before every request, no round-trip
```

### Memory vs State (critical distinction)

- **State**: dict, you write/read by key. Known facts. Survives sessions with `user:` / `app:` prefix.
- **Memory**: corpus, you search by query. The service decides relevance. Whole conversations ingested.

---

## Wiring example

```python
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

runner = Runner(
    app_name="my_app",
    agent=root_agent,
    session_service=session_service,
    memory_service=memory_service,
)

# After session completes:
await memory_service.add_session_to_memory(completed_session)
```