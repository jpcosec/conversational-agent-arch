"""Base comun de agentes LLM (fase 2.1): ver ``kb_agent.agents.base`` para el
diseño completo y las diferencias frente a ``google-adk``.
"""
from __future__ import annotations

from .base import (
    Agent,
    AfterModelCallback,
    AfterToolCallback,
    BeforeModelCallback,
    BeforeToolCallback,
    LlmRequest,
    LlmResponse,
    Tool,
    ToolCall,
)
from .gate import (
    GateAgent,
    GateVerdict,
    PREFILTER_CRITERION_ID,
    render_gate_criteria,
    response_claims_completed_action,
)

__all__ = [
    "Agent",
    "LlmRequest",
    "LlmResponse",
    "Tool",
    "ToolCall",
    "BeforeModelCallback",
    "AfterModelCallback",
    "BeforeToolCallback",
    "AfterToolCallback",
    "GateAgent",
    "GateVerdict",
    "PREFILTER_CRITERION_ID",
    "render_gate_criteria",
    "response_claims_completed_action",
]
