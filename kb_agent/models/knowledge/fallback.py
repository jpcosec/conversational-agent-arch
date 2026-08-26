from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class FallbackRule(IndexProxies):
    """Regla de fallback: qué hacer cuando no hay contexto suficiente.

    Caso especial de RuleAtom. Cuando el Ontologizador produce
    un CompiledDocument vacío (is_empty=True), el Conversador
    usa este mensaje en vez de alucinar.
    """

    __family__ = "conversation"
    __semantics__ = {
        "type": ["knowledge", "fallback"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: fallback
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Fallback Message

⸢rev•fallback_message⸥

## Conditions

⸢rev•conditions⸥
""".strip()

    id: str = Field(
        description="Stable fallback identifier, conventionally 'fallback-<slug>'."
    )
    title: str = Field(
        description="Short, descriptive title (e.g. 'Sin contexto', 'Tool no disponible')."
    )
    fallback_message: str = Field(
        description="The exact message the agent should say when fallback activates."
    )
    conditions: str = Field(
        default="",
        description="When this fallback applies (e.g. 'empty context', 'tool unavailable', 'ambiguous query').",
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. conversation:fallback, self:limites.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source.",
    )