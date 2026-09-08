from enum import StrEnum
from typing import Annotated

from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag

class StepKind(StrEnum):
    """Comportamiento del paso conversacional.

    Define qué ocurre dentro del step. El nombre (title) es libre;
    el kind determina el tratamiento en runtime y qué campos aplican.
    """

    INTERACCION_SIMPLE = "interaccion_simple"
    OBTENCION_DATOS = "obtencion_datos"
    HANDOUT = "handout"
    LLAMADO_TOOL = "llamado_tool"


class ConversationStep(IndexProxies):
    """Nodo del diagrama de conversación.

    Define un paso en el flujo conversacional: qué debe hacer el agente en
    este paso y qué slots recolectar. A dónde puede transicionar, qué átomos
    lo groundean y qué tool ejecuta NO son campos: son aristas tipadas de
    kgdb (``transitions_to``, ``grounded_by``, ``uses_tool``, RelationDoc de
    la KB) que el runtime lee del grafo (``kb_agent.knowledge.flow``).
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
kind: ⸢rev•kind⸥
tags: ⸢rev•tags⸥
domain_ref: ⸢optrev•domain_ref⸥
summary: ⸢rev•summary⸥
embedding: ⸢optrev•embedding⸥
parent: ⸢optrev•parent⸥
semantic_anchors: ⸢optrev•semantic_anchors⸥
---

# ⸢render•title⸥

## Instructions

⸢rev•instructions⸥

## Required Slots

⸢rev•required_slots⸥

## Handout Target

⸢optrev•handout_target⸥

## Completion Condition

⸢optrev•completion_condition⸥
""".strip()

    id: str = Field(
        description="Stable step identifier, conventionally 'step-<slug>' or 'conversation:steps.<name>'."
    )
    title: str = Field(
        description="Short, descriptive, freely-editable name for this conversation step."
    )
    kind: StepKind = Field(
        default=StepKind.INTERACCION_SIMPLE,
        description=(
            "Behavioral type of the step: interaccion_simple (send/respond), "
            "obtencion_datos (capture slots), handout (escalate/derive), "
            "llamado_tool (execute a tool)."
        ),
    )
    instructions: str = Field(
        description="What the agent should do at this step: how to guide the user, what to ask."
    )
    required_slots: str = Field(
        default="",
        description="List or description of information slots that must be filled during this step."
    )
    handout_target: str = Field(
        default="",
        description="For kind=handout: where to escalate/derive (human team, other flow, external service)."
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