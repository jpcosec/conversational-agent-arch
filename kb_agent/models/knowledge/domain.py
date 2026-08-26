from enum import StrEnum
from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE


class AtomQuestion(StrEnum):
    WHAT = "what"
    WHY = "why"
    HOW = "how"
    HOW_NOT = "how_not"
    WHEN = "when"
    WHERE = "where"
    FOR_WHOM = "for_whom"


AtomTag = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_.-]*$",
        description="Namespaced semantic tag in the form namespace:value.",
    ),
]


class DomainAtom(IndexProxies):
    """Hecho de conocimiento factual de negocio.

    Describe realidades de negocio: catálogo de productos,
    horarios de atención, ubicación, identidad del negocio.
    """

    __family__ = "domain"
    __semantics__ = {
        "type": ["knowledge", "domain"],
        "workspace": ["knowledge"],
    }
    __template__ = f"""---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
five_wh_one_plus: ⸢rev•five_wh_one_plus⸥
atom_type: domain
tags: ⸢rev•tags⸥
domain_ref: ⸢optrev•domain_ref⸥
provenance: ⸢optrev•provenance⸥
{INDEX_PROXY_TEMPLATE}
---

# ⸢render•title⸥

## Answer

⸢rev•answer⸥
""".strip()

    id: str = Field(
        description="Stable, unique atom identifier, conventionally 'atom-<slug>'."
    )
    title: str = Field(
        description="Short, descriptive title for this knowledge unit."
    )
    five_wh_one_plus: AtomQuestion = Field(
        description="The single 5WH1+ question this atom answers."
    )
    answer: str = Field(
        description="The curated factual answer to the selected 5WH1+ question."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags for retrieval, e.g. domain:catalogo, domain:pizzeria.",
    )
    domain_ref: str | None = Field(
        default=None,
        description="Identifier of the business domain this atom belongs to (e.g. 'don-peppe', 'heladeria').",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source of this knowledge.",
    )