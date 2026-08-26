from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class StrategyRule(IndexProxies):
    """Estrategia general de interacción conversacional.

    Define el enfoque, objetivos y prioridades que guían
    cómo el agente aborda la conversación en su conjunto.
    No es un step ni una regla condicional — es una directriz
    estratégica de alto nivel.
    """

    __semantics__ = {
        "type": ["knowledge", "strategy"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: strategy
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Goal

⸢rev•goal⸥

## Approach

⸢rev•approach⸥

## Priorities

⸢optrev•priorities⸥
""".strip()

    id: str = Field(
        description="Stable strategy identifier, conventionally 'strategy-<slug>'."
    )
    title: str = Field(
        description="Short title (e.g. 'Estrategia de venta', 'Estrategia de soporte')."
    )
    goal: str = Field(
        description="Primary goal of this conversational strategy. What the agent should achieve."
    )
    approach: str = Field(
        description="How to achieve the goal: guiding principles, structural preferences, decision heuristics."
    )
    priorities: str = Field(
        default="",
        description="Ordered priorities when goals conflict. What to favor when trade-offs arise."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. conversation:strategy, domain:pizzeria.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source.",
    )