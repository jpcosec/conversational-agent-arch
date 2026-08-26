from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class TraitAtom(IndexProxies):
    """Descriptor de una característica cognitiva o de comportamiento del usuario.

    No tiene 'answer' — es un identificador reutilizable que múltiples
    usuarios referencian desde SQL (UserTraits.trait_id). El Perfilador
    mapea texto del usuario a TraitAtom vía Gemini.
    """

    __semantics__ = {
        "type": ["knowledge", "trait"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: trait
tags: ⸢rev•tags⸥
category: ⸢optrev•category⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Description

⸢rev•description⸥
""".strip()

    id: str = Field(
        description="Stable trait identifier, conventionally 'trait-<slug>'. Referenced from SQL UserTraits.trait_id."
    )
    title: str = Field(
        description="Short, descriptive title for this trait (e.g. 'Sin gluten', 'Vegetariano')."
    )
    description: str = Field(
        description="Human-readable description of this trait and its implications for the conversation."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. user:traits.celiaco, user:traits.vegetariano.",
    )
    category: str | None = Field(
        default=None,
        description="Trait category for grouping: dietary, preference, behavior, demographic.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source of this trait definition.",
    )