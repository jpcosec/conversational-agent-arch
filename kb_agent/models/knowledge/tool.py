from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc

from .domain import AtomTag


class ToolAtom(StructuredNLDoc):
    """Esquema JSON de una API o función externa.

    El Ontologizador convierte estos átomos en function_declarations
    para el LLM en tiempo real.
    """

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