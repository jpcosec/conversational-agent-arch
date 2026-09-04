from pydantic import Field

from sldb import StructuredNLDoc


class CompositionDoc(StructuredNLDoc):
    __semantics__ = {
        "type": ["documentation", "composition"],
        "workspace": ["desk", "materializations"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
target_path: ⸢rev•target_path⸥
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
---

⸢rev•body⸥
""".strip()

    id: str = Field(
        description="Stable composition identifier, conventionally 'composition-<slug>'."
    )
    title: str = Field(
        description="Human-readable title of the composed document."
    )
    target_path: str = Field(
        description="Repository-relative output path that this composition materializes to."
    )
    body: str = Field(
        description="Full Markdown source of the composed document, including headings, prose, links, and ![[transclusions]]."
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Namespaced semantic tags for retrieval and grouping."
    )
    provenance: str | None = Field(
        default=None,
        description="Optional authoritative source path or URI for this composition document."
    )
