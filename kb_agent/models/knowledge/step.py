from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class ConversationStep(IndexProxies):
    """Nodo del diagrama de conversación.

    Define un paso en el flujo conversacional: qué debe hacer
    el agente en este paso, qué slots recolectar, a dónde
    puede transicionar, y qué átomos groundean este step.
    """

    __family__ = "conversation"
    __semantics__ = {
        "type": ["knowledge", "step"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: step
tags: ⸢rev•tags⸥
domain_ref: ⸢optrev•domain_ref⸥
summary: ⸢optrev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Instructions

⸢rev•instructions⸥

## Required Slots

⸢rev•required_slots⸥

## Allowed Transitions

⸢rev•allowed_transitions⸥

## Grounding Atoms

⸢rev•grounding_atoms⸥

## Completion Condition

⸢optrev•completion_condition⸥
""".strip()

    id: str = Field(
        description="Stable step identifier, conventionally 'step-<slug>' or 'conversation:steps.<name>'."
    )
    title: str = Field(
        description="Short, descriptive title for this conversation step."
    )
    instructions: str = Field(
        description="What the agent should do at this step: how to guide the user, what to ask."
    )
    required_slots: str = Field(
        default="",
        description="List or description of information slots that must be filled during this step."
    )
    allowed_transitions: str = Field(
        default="",
        description="List or description of steps that can follow this one (e.g. 'booking', 'onboarding')."
    )
    grounding_atoms: str = Field(
        default="",
        description="List or description of atom ids that ground this step's instructions."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. conversation:steps.booking, conversation:steps.onboarding.",
    )
    domain_ref: str | None = Field(
        default=None,
        description="Identifier of the business domain this step belongs to.",
    )
    completion_condition: str | None = Field(
        default=None,
        description="Condition under which this step is considered complete (e.g. 'all slots filled', 'tool executed successfully').",
    )