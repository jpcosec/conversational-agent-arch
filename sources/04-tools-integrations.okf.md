# Tools and Integrations

type: reference
topic: tools-integrations
source: https://github.com/google/adk-python/tree/main/src/google/adk/tools

## Tool types

| Tool type | Path | Description |
|-----------|------|-------------|
| Function tool | `google.adk.tools.FunctionTool` | Any Python function → tool |
| MCP tool | `google.adk.tools.mcp_tool` | Model Context Protocol servers |
| OpenAPI tool | `google.adk.tools.openapi_tool` | REST APIs from OpenAPI specs |
| Bash tool | `google.adk.tools.BashTool` | Shell command execution |
| Computer use | `google.adk.tools.computer_use` | Browser/desktop automation |
| Google Search | `google.adk.tools.GoogleSearchTool` | Web search |
| Vertex AI Search | `google.adk.tools.VertexAiSearchTool` | Enterprise search |
| BigQuery | `google.adk.tools.bigquery` | SQL queries + metadata |
| Bigtable | `google.adk.tools.bigtable` | Bigtable queries |
| Spanner | `google.adk.tools.spanner` | Spanner queries |
| Pub/Sub | `google.adk.tools.pubsub` | Pub/Sub messaging |
| GCS | `google.adk.tools.gcs` | Cloud Storage operations |
| Data Agent | `google.adk.tools.data_agent` | Data Agent integration |
| API Hub | `google.adk.tools.apihub_tool` | API Hub integration |
| Application Integration | `google.adk.tools.application_integration_tool` | App Integration connector |
| Long-running | `google.adk.tools.LongRunningTool` | Async task with status polling |
| Load memory | `google.adk.tools.load_memory` | Cross-session recall |
| Preload memory | `google.adk.tools.preload_memory` | Auto memory preload |
| Agent tool | `google.adk.tools.AgentTool` | Tool wrapping sub-agent |
| Transfer tool | `google.adk.tools.TransferToAgentTool` | Transfer control to agent |
| Code execution | `google.adk.code_executors` | Sandboxed code (Python, bash) |

## MCP (Model Context Protocol)

- Full MCP client support: stdio, SSE, Streamable HTTP.
- Tools, resources, prompts all accessible.
- Authentication support (OAuth2, service account, mTLS).
- Session management via MCP session manager.
- MCP servers run as subprocesses (stdio) or HTTP (SSE/Streamable).

```python
from google.adk.tools.mcp_tool import MCPToolset

mcp_tools = MCPToolset.from_server(
    command="python", args=["-m", "mcp_server"]
)
```

## Code Executors

| Executor | Path | Use case |
|----------|------|----------|
| UnsafeLocalCodeExecutor | `code_executors.unsafe_local_code_executor` | Dev only |
| ContainerCodeExecutor | `code_executors.container_code_executor` | Docker container |
| VertexAiCodeExecutor | `code_executors.vertex_ai_code_executor` | GCP managed |
| AgentEngineSandboxCodeExecutor | `code_executors.agent_engine_sandbox_code_executor` | Vertex AI sandbox |
| GKECodeExecutor | `code_executors.gke_code_executor` | GKE cluster |

## Integrations (Google Cloud ecosystem)

| Integration | Path | Function |
|-------------|------|----------|
| BigQuery | `integrations.bigquery` | Query, metadata, search, data insights |
| Bigtable | `integrations.bigtable` | HBase queries |
| Spanner | `integrations.spanner` | SQL queries, admin, search |
| Pub/Sub | `integrations.eventarc` | Event-driven agents |
| GCS | `integrations.gcs` | Read/write objects |
| Firestore | `integrations.firestore` | Memory + session services |
| Redis | `integrations.redis` | Session service |
| Slack | `integrations.slack` | Slack bot runner |
| Agent Registry | `integrations.agent_registry` | GCP Agent Registry |
| Skill Registry | `integrations.skill_registry` | GCP Skill Registry |
| Parameter Manager | `integrations.parameter_manager` | Parameter store |
| Secret Manager | `integrations.secret_manager` | Secrets access |
| Agent Identity | `integrations.agent_identity` | Crypto agent identity |
| Sandbox | `integrations.vmaas` | VM-based sandbox |

## Third-party integrations

- **LangChain**: `integrations.langchain.LangchainTool` — wrap LangChain tools
- **CrewAI**: `integrations.crewai.CrewaiTool` — wrap CrewAI tools
- **E2B**: `integrations.e2b` — E2B code sandbox environment
- **Daytona**: `integrations.daytona` — Daytona dev environments
- **OCI**: `integrations.oci` — Oracle OCI GenAI LLM

## Tool Confirmation (HITL)

- Built-in flow for human-in-the-loop tool execution.
- `tool_confirmation=True` on tool definition.
- Framework pauses and requests user confirmation before executing.
- Custom confirmation prompts supported.