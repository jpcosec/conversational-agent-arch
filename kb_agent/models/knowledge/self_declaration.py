from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class SelfDeclaration(IndexProxies):
    """Declaración de identidad del agente (whoami).

    Responde "quién soy, qué soy, para quién trabajo".
    No es un hecho de dominio ni una regla.
    """

    __semantics__ = {
        "type": ["knowledge", "self"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: self
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Statement

⸢rev•statement⸥
""".strip()

    id: str = Field(
        description="Stable declaration identifier, conventionally 'self-<slug>'."
    )
    title: str = Field(
        description="Short title (e.g. 'Who I am', 'Que soy')."
    )
    statement: str = Field(
        description="Natural language statement about who the agent is, its role, and who it represents."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. self:whoami.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source.",
    )