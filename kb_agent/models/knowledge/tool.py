from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class ToolAtom(IndexProxies):
    """Esquema JSON de una API o función externa.

    El Ontologizador convierte estos átomos en function_declarations
    para el LLM en tiempo real.
    """

    __family__ = "self"
    __semantics__ = {
        "type": ["knowledge", "tool"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: tool
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Description

⸢rev•description⸥

## Parameters

```json
⸢rev•parameters⸥
```
""".strip()

    id: str = Field(
        description="Stable, unique tool identifier, conventionally 'tool-<slug>'."
    )
    title: str = Field(
        description="Short, descriptive title for this tool."
    )
    description: str = Field(
        description="Natural language description of what this tool does and when to call it."
    )
    parameters: str = Field(
        description="JSON schema string representing the tool's parameters (function_declarations format)."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. self:tools, conversation:steps.booking.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source of this tool definition.",
    )