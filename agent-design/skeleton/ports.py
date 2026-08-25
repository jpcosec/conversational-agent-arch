"""Puertos (interfaces) hacia los repos reales.

El agente NO conoce kgdb/sldb/LLM directamente. Habla con estos puertos.
Cada uno se implementa después como adaptador fino sobre el repo real,
usando su CLI (no sus APIs internas) para sobrevivir refactors.
"""
from __future__ import annotations

from typing import Protocol

from kinds import Atom, Edge, Node, TypedForm, Verdict


class GraphPort(Protocol):
    """Adaptador sobre kgdb (usar `kgdb query/get/ingest` por CLI)."""

    def ask(self, query: str) -> list[Node]:
        """Paso 2: consultar el grafo tipado. Vacío = miss."""
        ...

    def add_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...


class LLMPort(Protocol):
    """Adaptador sobre el LLM. DEBE devolver formas tipadas, no prosa."""

    def translate(self, nl_input: str, context: list[Node]) -> list[TypedForm]:
        """Paso 3: NL -> formas tipadas. Prompt fuerza el grammar."""
        ...


class GatePort(Protocol):
    """Adaptador sobre el lifecycle de proposiciones (Matrix)."""

    def judge(self, form: TypedForm, context: list[Node]) -> Verdict:
        """Paso 4: S_i (¿bien tipado?) luego V_i (¿verdadero?)."""
        ...


class StorePort(Protocol):
    """Adaptador sobre sldb (usar `sldb docs/fields` por CLI)."""

    def save_atom(self, atom: Atom) -> str:
        """Paso 5: persistir átomo tipado + provenance. Devuelve id."""
        ...
