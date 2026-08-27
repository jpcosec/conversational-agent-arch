from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompiledDocument:
    """Documento compilado producido por el compilador, consumido por el conversador.

    El contexto viene ESTRUCTURADO POR ROL SEMANTICO (doctrina KB), no como una
    bolsa plana de texto. El conversador arma su prompt desde ``persona`` (self:*)
    y ``strategy`` (conversation:strategy); el orquestador usa ``fallback_text``
    (conversation:fallback) cuando no hay contexto. Nada de esto se hardcodea.
    """

    scenario: str
    question: str
    #: Traits del usuario resueltos contra su TraitAtom en la KB (no solo el
    #: id): {trait_id, title, description, category, confidence, source}.
    user_traits: list[dict[str, Any]] = field(default_factory=list)
    #: Subconjunto DomainAtom/RuleAtom del ``bundle`` (mismo shape que antes:
    #: id/body/tags/title/family). Ya no es "todo el modelo", es lo que
    #: selecciono el bundle justificado (ver ``bundle``).
    domain_facts: list[dict[str, str]] = field(default_factory=list)
    rules: list[dict[str, str]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    #: Bundle justificado del turno: union sin duplicados de similitud
    #: (contra la pregunta, cualquier familia), grounding del step activo,
    #: piso de seguridad (RuleAtom conversation:security, siempre) y traits
    #: del usuario. Cada entrada: {doc_id, family, motivo, score}.
    #: ``domain_facts`` y ``rules`` arriba son la proyeccion tipada de este
    #: bundle (ver ``ContextCompiler._build_bundle``).
    bundle: list[dict[str, Any]] = field(default_factory=list)
    #: Ultimos N mensajes de ``chat_history`` del usuario, cronologicos,
    #: {role, content}. NO incluye el turno en curso (eso es ``question``).
    history: list[dict[str, str]] = field(default_factory=list)
    grounding_atoms: list[str] = field(default_factory=list)
    flow_node: str | None = None
    allowed_transitions: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    system_turn: dict | None = None
    is_empty: bool = False
    # ── contexto estructurado por rol semantico (deshardcodeo) ──
    persona: dict[str, str] = field(default_factory=dict)   # self:whoami / estilo / limites
    strategy: str = ""                                       # conversation:strategy
    fallback_text: str = ""                                  # conversation:fallback

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}