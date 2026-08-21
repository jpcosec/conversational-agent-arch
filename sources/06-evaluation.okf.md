# Evaluation and Optimization

type: reference
topic: evaluation
source: https://github.com/google/adk-python/tree/main/src/google/adk/evaluation

## Evaluation framework

Location: `google.adk.evaluation`

### EvalSet format

```json
{
  "eval_set": {
    "name": "my_evals",
    "cases": [
      {
        "name": "test_1",
        "message": {"role": "user", "parts": [{"text": "Hello"}]},
        "expected_tool_use": [{"tool_name": "roll_die"}],
        "expected_criteria": {"response_relevance": ">= 3"}
      }
    ]
  }
}
```

### Evaluator types

| Evaluator | Description |
|-----------|-------------|
| FinalResponseMatchV1 | Exact match on final response |
| FinalResponseMatchV2 | Regex/fuzzy match |
| LlmAsJudge | LLM judges response quality |
| RubricBasedEvaluator | Rubric-based scoring |
| MultiTurnTaskSuccessEvaluator | Task completion across turns |
| MultiTurnToolUseQualityEvaluator | Tool call quality |
| MultiTurnTrajectoryQualityEvaluator | Path quality |
| SafetyEvaluator | Safety checks |
| HallucinationV1 | Hallucination detection |
| CustomMetricEvaluator | User-defined metrics |

### CLI usage

```bash
adk eval agent_dir/ eval_set.evalset.json
```

### Simulation

```python
from google.adk.evaluation.simulation import LlmBackedUserSimulator

sim = LlmBackedUserSimulator(persona="tech_savvy_user")
# Runs agent against simulated user conversations
```

- `PreBuiltPersonas`: common user archetypes.
- `PerTurnUserSimulatorQuality`: evaluates per-turn quality.
- Supports audio simulation via `LlmAudioUserSimulator` and `CloudTtsLlm`.

## Optimization

Location: `google.adk.optimization`

### AgentOptimizer

- Clusters real-world failures from evaluation.
- Suggests improved system instructions automatically.
- Uses GEPA (Gemini Enterprise Platform Agent) as optimizer.

```python
from google.adk.optimization import SimplePromptOptimizer

optimizer = SimplePromptOptimizer()
optimized_instruction = optimizer.optimize(
    agent, eval_results, eval_set
)
```

## Observability

Via OpenTelemetry:

- `telemetry.google_cloud` for GCP export.
- `telemetry.sqlite_span_exporter` for local dev.
- Plugin system for custom tracing (`AutoTracingPlugin`).
- BigQuery agent analytics plugin.

## Key patterns

1. **Simulate → Evaluate → Optimize** loop built in.
2. EvalSets are version-controlled JSON, runs with a single CLI command.
3. Custom metrics via subclassing `CustomMetricEvaluator`.
4. LLM-as-judge for subjective quality assessment.