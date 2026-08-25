"""Compilador de contexto: navega SLDB + KGDB + SQL para producir CompiledDocument.

Flujo:
  1. Resuelve scenario (argumento -> session_state -> default)
  2. Busca atoms relevantes en SLDB via búsqueda semántica (domain, atom_type)
  3. [Opcional] Navega grafo KGDB para resolver nodo de flujo, transiciones, slots
  4. Compila a un CompiledDocument con facts, rules, tools, grounding + flujo
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import UserTraits

from .compiled_document import CompiledDocument
from .kgdb_reader import KGDBReader
from .sldb_reader import SLDBReader


class SessionStateLike(Protocol):
    active_domain: str | None


@dataclass(slots=True)
class ContextCompiler:
    reader: SLDBReader
    kgdb: KGDBReader | None = None
    identity_session: Session | None = None
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None

    def compile(
        self,
        *,
        question: str,
        user_id: int | None,
        scenario: str | None = None,
        trigger: str = "user",
        session_state: SessionStateLike | None = None,
    ) -> CompiledDocument:
        resolved_scenario = self._resolve_scenario(
            user_id=user_id,
            scenario=scenario,
            trigger=trigger,
            session_state=session_state,
        )

        domain_facts = self._find_atoms("domain", resolved_scenario)
        rules = self._find_atoms("rule", resolved_scenario)
        tools = self._find_tools(resolved_scenario)
        user_traits = self._load_user_traits(user_id)

        doc = CompiledDocument(
            scenario=resolved_scenario,
            question=question,
            user_traits=user_traits,
            domain_facts=domain_facts,
            rules=rules,
            tools=tools,
            is_empty=not domain_facts and not rules,
        )

        # Enriquecer con KGDB si hay grafo
        if self.kgdb is not None and resolved_scenario:
            self._augment_from_kgdb(doc, resolved_scenario)

        return doc

    def _resolve_scenario(
        self,
        *,
        user_id: int | None,
        scenario: str | None,
        trigger: str,
        session_state: SessionStateLike | None,
    ) -> str:
        if scenario:
            return scenario

        active_domain = getattr(session_state, "active_domain", None)
        if active_domain:
            return active_domain

        if trigger != "cron" and user_id is not None and self.session_state_loader is not None:
            loaded_state = self.session_state_loader(user_id)
            loaded_domain = getattr(loaded_state, "active_domain", None) if loaded_state is not None else None
            if loaded_domain:
                return loaded_domain

        return self.default_scenario()

    def default_scenario(self) -> str:
        scenarios = sorted(
            {
                tag.split(":", 1)[1]
                for r in self._records()
                for tag in r.get("tags", [])
                if tag.startswith("domain:")
            }
        )
        top_level = [s for s in scenarios if "." not in s]
        return top_level[0] if top_level else scenarios[0] if scenarios else ""

    def _records(self) -> list[dict[str, Any]]:
        return self.reader.find("type.knowledge.atom", search_in="semantic")

    def _find_atoms(self, atom_type: str, scenario: str) -> list[dict[str, str]]:
        """Busca atoms por tipo + escenario via búsqueda semántica SLDB."""
        matched = self.reader.find(f"atom_type:{atom_type}")
        # filtrar en Python por escenario (search_records trata el string completo como un término)
        filtered = [
            m for m in matched
            if _matches_domain_tag(m.get("tags", []), scenario)
        ]
        return sorted(
            [{"id": m["id"], "body": m.get("answer", "")} for m in filtered],
            key=lambda x: x["id"],
        )

    def _find_tools(self, scenario: str) -> list[dict[str, Any]]:
        """Busca tool atoms y devuelve su schema JSON."""
        matched = self.reader.find(f"atom_type:tool")
        filtered = [
            m for m in matched
            if _matches_domain_tag(m.get("tags", []), scenario)
        ]
        tools = []
        for m in filtered:
            answer = m.get("answer", "")
            schema = self._parse_tool_schema(answer)
            if schema:
                tools.append(schema)
        return sorted(tools, key=lambda t: t.get("name", ""))

    @staticmethod
    def _parse_tool_schema(text: str) -> dict[str, Any] | None:
        """Extrae el schema JSON de la respuesta de un tool atom."""
        import re, json
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    # ── enriquecimiento KGDB ────────────────────────────────────

    def _augment_from_kgdb(self, doc: CompiledDocument, scenario: str) -> None:
        """Enriquece el documento compilado con datos del grafo KGDB."""
        if self.kgdb is None:
            return
        # Buscar nodos de flujo que coincidan con el escenario
        flow_nodes = self.kgdb.find_nodes_by_type("conversation_flow_node")
        # Intentar encontrar un nodo raíz para el escenario
        for fn in flow_nodes:
            schema = self.kgdb.get_flow_node(fn)
            if schema and self._matches_scenario_in_node(schema, scenario):
                doc.flow_node = fn
                transitions = self.kgdb.get_next_transitions(fn)
                doc.allowed_transitions = [t["to"] for t in transitions]
                doc.grounding_atoms = self.kgdb.get_grounding_atoms(fn)
                break

    @staticmethod
    def _matches_scenario_in_node(schema: dict, scenario: str) -> bool:
        tags = schema.get("semantics", {}).get("tags", []) if isinstance(schema, dict) else []
        if isinstance(tags, str):
            tags = [tags]
        return any(scenario in t for t in tags)

    def _load_user_traits(self, user_id: int | None) -> list[str]:
        if user_id is None or self.identity_session is None:
            return []
        statement = select(UserTraits.trait_id).where(UserTraits.user_id == user_id).order_by(UserTraits.trait_id)
        return list(self.identity_session.scalars(statement))


def _matches_domain_tag(tags: list[str], scenario: str) -> bool:
    if not scenario or not tags:
        return False
    prefix = "domain:"
    domain_tag = f"{prefix}{scenario}"
    return any(t == domain_tag or t.startswith(f"{domain_tag}.") for t in tags)


def compile_context(
    question: str,
    user_id: int | None,
    scenario: str | None = None,
    trigger: str = "user",
    session_state: SessionStateLike | None = None,
    reader: SLDBReader | None = None,
    identity_session: Session | None = None,
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None,
    kgdb: KGDBReader | None = None,
) -> CompiledDocument:
    compiler = ContextCompiler(
        reader=reader or SLDBReader(kb_root="."),
        identity_session=identity_session,
        session_state_loader=session_state_loader,
        kgdb=kgdb,
    )
    return compiler.compile(
        question=question,
        user_id=user_id,
        scenario=scenario,
        trigger=trigger,
        session_state=session_state,
    )