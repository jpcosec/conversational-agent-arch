from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomQuestion, AtomTag

class RuleAtom(IndexProxies):
    """Heurística o restricción de comportamiento.

    Define condiciones bajo las cuales el agente debe actuar
    de una forma determinada. Acota la libertad generativa
    del Conversador.
    """

    __family__ = "domain"
    __semantics__ = {
        "type": ["knowledge", "rule"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
five_wh_one_plus: ⸢rev•five_wh_one_plus⸥
atom_type: rule
tags: ⸢rev•tags⸥
applies_to: ⸢optrev•applies_to⸥
provenance: ⸢optrev•provenance⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Answer

⸢rev•answer⸥

## Conditions

⸢rev•conditions⸥
""".strip()

    id: str = Field(
        description="Stable, unique rule identifier, conventionally 'rule-<slug>'."
    )
    title: str = Field(
        description="Short, descriptive title for this rule."
    )
    five_wh_one_plus: AtomQuestion = Field(
        description="The single 5WH1+ question this rule answers."
    )
    answer: str = Field(
        description=(
            "The rule body: prescribed behavior, constraint, or heuristic "
            "the agent must follow."
        )
    )
    conditions: str = Field(
        default="",
        description="When this rule applies. Natural language description of preconditions.",
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. domain:reglas.reservas, conversation:fallback.",
    )
    applies_to: str | None = Field(
        default=None,
        description="Scope identifier: which conversation, domain, or step this rule applies to.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source of this rule.",
    )