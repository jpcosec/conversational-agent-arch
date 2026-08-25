# Result Summary

- run_id: `20260825-025705-task-implementar-pausa-de-tools-en-router`
- child session path: `unavailable-from-api-context`
- session_sha256: `unavailable-from-api-context`

## Scope completed

Implemented only the router state-machine pause/resume behavior for tool calls in `kb_chat_ui/state_machine.py`, preserving the existing debounce flow.

## Changed surfaces

- `kb_chat_ui/state_machine.py`
- `tests/test_state_machine.py`

## Validation

- `pytest tests/test_state_machine.py -q` → `12 passed`

## Notes for review

- `draft_response()` responses shaped as `{ "function_call": {...} }` now pause the state machine in `waiting_tool`.
- Tool results are re-injected as a system turn (`role='system'`) and resume drafting without recompiling context.
- Tool timeouts resume drafting with a serialized timeout error system turn after `TOOL_TIMEOUT_MS`.
- User messages received while waiting on a tool are queued only in `SessionState.buffer["tool_wait"]`; debounce buffering remains untouched.
