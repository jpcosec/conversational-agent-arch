"""Tipos núcleo del agente. Deliberadamente pequeños.

Estos tipos son el "lenguaje tipado" sobre el que trabaja el agente.
No dependen de kgdb/sldb todavía: son el contrato mínimo que luego
se adapta a esos repos (kgdb.KnowledgeNode, sldb.StructuredNLDoc).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


# --- Salida tipada del LLM (contrato). El LLM SOLO puede emitir esto. ---
SexpKind = Literal["think", "rel", "command", "model", "unl"]


@dataclass
class TypedForm:
    """Una forma tipada emitida por el LLM. Reemplaza texto libre."""
    kind: SexpKind
    head: str                      # predicado / nombre de comando / etc.
    args: list[str] = field(default_factory=list)
    raw: str = ""                  # s-expr original, para trazabilidad


# --- Gate de sentido (Matrix: S_i x V_i) ---
class Sense(str, Enum):
    SINNVOLL = "sinnvoll"      # bien tipado y evaluable
    SINNLOS = "sinnlos"        # bien tipado pero tautología/contradicción
    UNSINNIG = "unsinnig"      # fuera de esquema: NO se guarda


@dataclass
class Verdict:
    sense: Sense
    truth: bool | None         # V_i: None si aún no evaluable
    reason: str = ""

    @property
    def storable(self) -> bool:
        # Solo guardamos lo bien tipado. unsinnig se rechaza.
        return self.sense is not Sense.UNSINNIG


# --- Provenance: Source -> Sample -> Atom ---
@dataclass
class Source:
    path: str
    sha256: str

@dataclass
class Sample:
    source: Source
    span: tuple[int, int]      # cut verificable dentro del source

@dataclass
class Atom:
    """Unidad de conocimiento tipada. Espejo minimal de knowledge/AtomDoc."""
    id: str
    title: str
    answer: str
    five_wh_one_plus: dict[str, str] = field(default_factory=dict)
    verdict: Verdict | None = None
    sample: Sample | None = None
    grounding: Literal["derived", "sampled", "validated"] = "derived"


# --- Nodo/arista canónico (adaptador a kgdb) ---
@dataclass
class Node:
    node_id: str
    node_type: str
    facets: dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    src: str
    dst: str
    relation_type: str
    facets: dict[str, Any] = field(default_factory=dict)


# --- Resultado del loop ---
@dataclass
class AgentResult:
    answer: str
    source: Literal["graph", "llm"]
    new_nodes: list[Node] = field(default_factory=list)
    new_edges: list[Edge] = field(default_factory=list)
    rejected: list[TypedForm] = field(default_factory=list)
