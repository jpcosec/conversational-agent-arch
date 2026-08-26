from pydantic import Field

from sldb import StructuredNLDoc
from .index_proxies import IndexProxies, INDEX_PROXY_TEMPLATE

from .domain import AtomTag


class GateCriterion(IndexProxies):
    """Criterio de validación post-draft para respuestas redactadas.

    La familia gate se activa sobre la respuesta ya redactada por el agente,
    no sobre la pregunta del usuario ni sobre el estado conversacional. El
    compilador de turno actual no consume esta familia (permanece invisible a
    ContextCompiler._MODEL_TYPES) y queda disponible para un gate futuro que
    consulte `type.knowledge.gate`.
    """

    __family__ = "gate"
    __semantics__ = {
        "type": ["knowledge", "gate"],
        "workspace": ["knowledge"],
    }
    __template__ = f"""---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: gate
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
{INDEX_PROXY_TEMPLATE}
---

# ⸢render•title⸥

## Criterion

⸢rev•criterion⸥

## Approval Condition

⸢rev•approval_condition⸥

## Rejection Action

⸢rev•rejection_action⸥
""".strip()

    id: str = Field(
        description="Stable gate identifier, conventionally 'gate-<slug>'."
    )
    title: str = Field(
        description="Short, descriptive title for this gate criterion."
    )
    criterion: str = Field(
        description="What must be evaluated in the drafted agent response."
    )
    approval_condition: str = Field(
        description="Condition under which the drafted response passes this criterion."
    )
    rejection_action: str = Field(
        description="What to do when the response fails: enqueue human review with the draft and rejection reason."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags for gate retrieval, e.g. gate:regulatorio.dosis, gate:corpus.",
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source.",
    )
