from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompiledDocument:
    """Documento compilado producido por el compilador, consumido por el conversador."""

    scenario: str
    question: str
    user_traits: list[str] = field(default_factory=list)
    domain_facts: list[dict[str, str]] = field(default_factory=list)
    rules: list[dict[str, str]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    grounding_atoms: list[str] = field(default_factory=list)
    flow_node: str | None = None
    allowed_transitions: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    system_turn: dict | None = None
    is_empty: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}