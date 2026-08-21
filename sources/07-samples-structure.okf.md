# Sample Agents Structure

type: reference
topic: samples
source: https://github.com/google/adk-python/tree/main/contributing/samples

## Core samples

| Sample | Path | What it shows |
|--------|------|---------------|
| hello_world | `core/hello_world/` | Basic agent with function tools + ToolContext state |
| empty_agent | `core/empty_agent/` | Minimal agent definition |
| quickstart | `core/quickstart/` | Quickstart pattern |
| input_output_schema | `core/input_output_schema/` | Pydantic I/O schemas |
| callbacks | `core/callbacks/` | Before/after agent callbacks |
| artifacts | `core/artifacts/` | Artifact service usage |
| abort | `core/abort/` | Abort patterns |
| logprobs | `core/logprobs/` | Log probabilities |
| runner_debug_example | `core/runner_debug_example/` | Runner debug features |
| app | `core/app/` | App container |

## Multi-agent samples

| Sample | Path | What it shows |
|--------|------|---------------|
| hello_world_ma | `multi_agent/hello_world_ma/` | Basic multi-agent |
| sub_agents | `multi_agent/sub_agents/` | Sub-agent delegation |
| single_turn_sub_agent | `multi_agent/single_turn_sub_agent/` | Single-turn mode |
| task_sub_agent | `multi_agent/task_sub_agent/` | Task mode with I/O schemas |
| three_layer_transfer | `multi_agent/three_layer_transfer/` | 3-level handoff |
| multi_agent_basic_config | `multi_agent/multi_agent_basic_config/` | Config-based multi-agent |
| multi_agent_llm_config | `multi_agent/multi_agent_llm_config/` | Per-agent LLM config |
| sub_agents_config | `multi_agent/sub_agents_config/` | Config-driven sub-agents |
| multi_agent_loop_config | `multi_agent/multi_agent_loop_config/` | Loop with sub-agents |
| multi_agent_seq_config | `multi_agent/multi_agent_seq_config/` | Sequential with sub-agents |

## Workflow samples

| Sample | Path | What it shows |
|--------|------|---------------|
| sequence | `workflows/sequence/` | Sequential DAG |
| route | `workflows/route/` | Conditional routing |
| loop | `workflows/loop/` | Looping via route |
| loop_self | `workflows/loop_self/` | Self-looping |
| loop_config | `workflows/loop_config/` | Config-based loop |
| fan_out_fan_in | `workflows/fan_out_fan_in/` | Parallel + JoinNode |
| dynamic_fan_out_fan_in | `workflows/dynamic_fan_out_fan_in/` | Dynamic parallel |
| dynamic_nodes | `workflows/dynamic_nodes/` | ctx.run_node() |
| nested_workflow | `workflows/nested_workflow/` | Workflow in workflow |
| agent_in_workflow | `workflows/agent_in_workflow/` | LlmAgent as node |
| node_as_tool | `workflows/node_as_tool/` | Node exposed as tool |
| parallel_worker | `workflows/parallel_worker/` | Parallel worker pattern |
| retry | `workflows/retry/` | Error handling + retry |
| state | `workflows/state/` | Workflow state management |
| message | `workflows/message/` | Workflow message passing |
| request_input | `workflows/request_input/` | Requesting user input |
| request_input_advanced | `workflows/request_input_advanced/` | Advanced input patterns |
| request_input_rerun | `workflows/request_input_rerun/` | Re-running input |
| node_output | `workflows/node_output/` | Custom node outputs |
| use_as_output | `workflows/use_as_output/` | Output shape control |
| multi_triggers | `workflows/multi_triggers/` | Multiple entry triggers |
| auth_api_key | `workflows/auth_api_key/` | API key auth in workflows |
| auth_oauth | `workflows/auth_oauth/` | OAuth in workflows |

## MCP samples

| Sample | Path | What it shows |
|--------|------|---------------|
| mcp_stdio_server_agent | `mcp/mcp_stdio_server_agent/` | Stdio MCP server |
| mcp_sse_agent | `mcp/mcp_sse_agent/` | SSE MCP server |
| mcp_sse_mtls_agent | `mcp/mcp_sse_mtls_agent/` | SSE + mutual TLS |
| mcp_streamablehttp_agent | `mcp/mcp_streamablehttp_agent/` | Streamable HTTP MCP |
| mcp_postgres_agent | `mcp/mcp_postgres_agent/` | Postgres via MCP |
| mcp_in_agent_tool_stdio | `mcp/mcp_in_agent_tool_stdio/` | MCP in tool |
| mcp_in_agent_tool_remote | `mcp/mcp_in_agent_tool_remote/` | Remote MCP tool |
| mcp_progress_callback_agent | `mcp/mcp_progress_callback_agent/` | Progress callbacks |
| mcp_service_account_agent | `mcp/mcp_service_account_agent/` | Service account auth |
| mcp_dynamic_header_agent | `mcp/mcp_dynamic_header_agent/` | Dynamic headers |
| mcp_server_side_sampling | `mcp/mcp_server_side_sampling/` | Server sampling |
| mcp_toolset_auth | `mcp/mcp_toolset_auth/` | Auth for MCP toolset |

## Model samples

| Sample | Path | What it shows |
|--------|------|---------------|
| hello_world_anthropic | `models/hello_world_anthropic/` | Claude integration |
| hello_world_gemma | `models/hello_world_gemma/` | Gemma local model |
| hello_world_gemma3_ollama | `models/hello_world_gemma3_ollama/` | Gemma via Ollama |
| hello_world_litellm | `models/hello_world_litellm/` | LiteLLM integration |
| hello_world_ollama | `models/hello_world_ollama/` | Ollama local |
| hello_world_nvidia | `models/hello_world_nvidia/` | Nvidia NIM |
| hello_world_apigeellm | `models/hello_world_apigeellm/` | Apigee LLM |
| interactions_api | `models/interactions_api/` | Interactions API |
| litellm variants | `models/` | Streaming, structured output, fallback |

## Integration samples

- bigquery, spanner, bigtable, pubsub, gcs, eventarc
- data_agent, agent_registry, gcp_skill_registry
- files_retrieval_agent, rag_agent, sandbox_computer_use
- slack_agent, jira_agent, toolbox_agent
- oauth_calendar_agent, oauth2_client_credentials
- gke_agent_sandbox, authn-adk-all-in-one (full auth flow)
- langchain_structured_tool_agent, langchain_youtube_search_agent
- crewai_tool_kwargs

## Other sample categories

| Category | Path | Contents |
|----------|------|----------|
| Live/streaming | `live/` | Bidirectional streaming, WebSocket |
| HITL | `hitl/` | Human-in-the-loop, tool confirmation, request input |
| Evaluation | `evaluation/` | Criteria, custom metrics, simulation |
| Context mgmt | `context_management/` | Cache, history, memory, rewind, session state |
| Code execution | `code_execution/` | Sandboxed code execution |
| Plugins | `plugins/` | Basic, debug logging, reflect retry |
| Patterns | `patterns/` | Context offloading, triage workflow, JSON passing |
| Environment | `environment_and_skills/` | E2B, Daytona, skills, skill toolset |
| Managed agent | `managed_agent/` | Remote agents, code execution, MCP |
| A2A | `a2a/` | Agent-to-Agent protocol (root, auth, HITL) |
| Config | `config/` | Agent Config YAML/JSON driven agents |
| Multimodal | `multimodal/` | Computer use, image generation, audio |
| Legacy workflows | `legacy_workflows/` | Old workflow patterns |