from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class CapabilityBoundary(IndexProxies):
    """Límite o restricción de capacidad del agente.

    Define qué no puede hacer el agente, bajo qué condiciones,
    y cómo debe comunicarlo.
    """

    __semantics__ = {
        "type": ["knowledge", "boundary"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: boundary
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Restriction

⸢rev•restriction⸥

## Conditions

⸢optrev•conditions⸥

## Escalation

⸢optrev•escalation⸥
""".strip()

    id: str = Field(
        description="Stable boundary identifier, conventionally 'boundary-<slug>'."
    )
    title: str = Field(
        description="Short title (e.g. 'No puedo reservar online', 'Limite de preguntas técnicas')."
    )
    restriction: str = Field(
        description="What the agent cannot do. Natural language description of the capability gap."
    )
    conditions: str = Field(
        default="",
        description="Conditions under which this restriction applies. When it can be bypassed, if ever."
    )
    escalation: str = Field(
        default="",
        description="How to escalate when this boundary is hit: handoff to human, suggest alternative channel, etc."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. self:limites, conversation:escalation.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source.",
    )