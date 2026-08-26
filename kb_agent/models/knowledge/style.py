from pydantic import Field

from sldb import StructuredNLDoc

from .domain import AtomTag


class StyleGuide(StructuredNLDoc):
    """Guia de estilo conversacional del agente.

    Define tono, registro, preferencias de fraseo, longitud
    de respuestas y otras directrices de comunicacion.
    """

    __semantics__ = {
        "type": ["knowledge", "style"],
        "workspace": ["knowledge"],
    }
    __template__ = """---
id: ⸢rev•id⸥
title: ⸢rev•title⸥
atom_type: style
tags: ⸢rev•tags⸥
provenance: ⸢optrev•provenance⸥
---

# ⸢render•title⸥

## Tone

⸢rev•tone⸥

## Language Register

⸢rev•language_register⸥

## Phrase Preferences

⸢optrev•phrase_preferences⸥

## Length Guidelines

⸢optrev•length_guidelines⸥
""".strip()

    id: str = Field(
        description="Stable style identifier, conventionally 'style-<slug>'."
    )
    title: str = Field(
        description="Short title (e.g. 'Estilo conversacional', 'Tono formal')."
    )
    tone: str = Field(
        description="Desired tone: friendly, formal, casual, empathetic, concise, etc."
    )
    language_register: str = Field(
        description="Linguistic register: vocabulary level, pronoun use (tu/usted), formality."
    )
    phrase_preferences: str = Field(
        default="",
        description="Preferred phrasing patterns, dispreferred expressions, opening/closing formulas."
    )
    length_guidelines: str = Field(
        default="",
        description="Desired response length: brief, moderate, detailed. Max sentences or words if applicable."
    )
    tags: list[AtomTag] = Field(
        default_factory=list,
        description="Namespaced semantic tags, e.g. self:estilo, conversation:strategy."
    )
    provenance: str | None = Field(
        default=None,
        description="Optional URL or path to the authoritative source."
    )