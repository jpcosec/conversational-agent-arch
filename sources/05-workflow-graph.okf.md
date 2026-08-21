# Graph-based Workflow Engine

type: architecture
topic: workflow-graph
source: https://github.com/google/adk-python/tree/main/src/google/adk/workflow
source-docs: https://github.com/google/adk-python/tree/main/docs/guides/workflow

## Core concept

Workflow = DAG of nodes (agents, functions, sub-workflows) with explicit edges.

```python
from google.adk import START, Workflow
from google.adk.workflow import JoinNode, node

workflow = Workflow(
    name="pipeline",
    edges=[(START, step_one, step_two)],
)
```

## Edge patterns

### Sequential chain
```python
edges=[(START, step_a, step_b)]  # a → b
```

### Parallel fan-out
```python
edges=[(START, step_a, (step_b, step_c))]  # a → b AND a → c
```

### Conditional routing
```python
# step_a must yield Event with route field = "route_x" or "route_y"
edges=[(START, step_a, {"route_x": step_b, "route_y": step_c})]
```

### Complex multi-edge
```python
edges=[
    ("START", step_a, step_b),          # a → b
    (step_b, step_c),                   # b → c
    (step_a, step_d),                   # a → d (parallel)
    (step_d, step_e),                   # d → e
]
```

## Node types

| Node | Import | What it does |
|------|--------|-------------|
| FunctionNode | `workflow.FunctionNode` | Python function as node |
| Node | `workflow.node` | Decorator: `@node` wraps function |
| JoinNode | `workflow.JoinNode` | Sync parallel branches, aggregate outputs |
| LlmAgent | `agents.LlmAgent` | LLM agent as node (mode=single_turn) |
| Workflow | `workflow.Workflow` | Nested workflow as node |
| Dynamic node | `ctx.run_node()` | Spawn nodes at runtime |

## JoinNode for parallel aggregation

```python
join_node = JoinNode(name="join_all")

async def aggregate(inputs: dict[str, Any]):
    yield Event(message=f"Combined: {inputs}")

edges=[("START", (step_a, step_b, step_c), join_node, aggregate)]
```

Workflow output rules:
- Single terminal → that node's output is workflow output.
- Multiple terminals → **fails** with ValueError unless JoinNode is used.
- JoinNode + aggregator → single aggregated output.

## Dynamic nodes

```python
async def dynamic_step(ctx):
    child = FunctionNode(name="spawned", fn=lambda x: x.upper())
    result = await ctx.run_node(child, "hello")
    return result
```

- Spawned nodes bypass static graph edges.
- Excluded from `max_concurrency` limit to prevent deadlocks.

## Workflow lifecycle

1. **Compilation**: edges → internal Graph, validated (no unconditional cycles, unique names, single START).
2. **Execution loop** (`_run_impl()`):
   - Schedule "ready" nodes (predecessors complete).
   - Run each in `NodeRunner` as asyncio task.
   - Wait, handle completion, cache outputs, buffer downstream triggers.
3. **Rehydration** (resume after interrupt):
   - Scan session history for previous events.
   - Reconstruct state, skip completed nodes, replay to interrupt point.
4. **Completion**: terminal node output becomes workflow output.

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `edges` | `list[EdgeItem]` | `[]` | Graph structure |
| `max_concurrency` | `int | None` | `None` (unlimited) | Throttle parallel nodes |
| `name` | `str` | required | Workflow/node name |

## Nested workflows

```python
inner = Workflow(name="inner", edges=[...])
outer = Workflow(name="outer", edges=[("START", inner)])
```

## Looping via route

```python
# step_a routes to step_b on "continue", or to "END" on "done"
edges=[("START", step_a, {"continue": step_b, "done": "END"}),
       (step_b, step_a)]  # back to step_a for loop
```

## Limitations

- **No unconditional cycles** — validator rejects them.
- **Multi-terminal parallel → fail** unless JoinNode aggregates.
- Dynamic nodes have no `max_concurrency` limit.

## Samples

- Sequence: `contributing/samples/workflows/sequence/`
- Fan-out/fan-in: `contributing/samples/workflows/fan_out_fan_in/`
- Loop: `contributing/samples/workflows/loop/`
- Conditional route: `contributing/samples/workflows/route/`
- Nested: `contributing/samples/workflows/nested_workflow/`
- Dynamic nodes: `contributing/samples/workflows/dynamic_nodes/`
- Retry: `contributing/samples/workflows/retry/`