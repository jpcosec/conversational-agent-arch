from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import UserTraits

from .sldb_reader import Atom, SLDBReader, ToolAtom


class SessionStateLike(Protocol):
    active_domain: str | None


@dataclass(slots=True)
class ContextCompiler:
    reader: SLDBReader
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
    ) -> dict[str, Any]:
        resolved_scenario = self._resolve_scenario(
            user_id=user_id,
            scenario=scenario,
            trigger=trigger,
            session_state=session_state,
        )
        rules = _serialize_atoms(self._select_atoms("rule", resolved_scenario))
        domain_facts = _serialize_atoms(self._select_atoms("domain", resolved_scenario))
        tools = [tool.json_schema for tool in self._select_tools(resolved_scenario)]
        payload = {
            "scenario": resolved_scenario,
            "question": question,
            "user_traits": self._load_user_traits(user_id),
            "rules": rules,
            "domain_facts": domain_facts,
            "tools": tools,
            "is_empty": not rules and not domain_facts,
        }
        return payload

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
        scenarios = sorted({
            suffix
            for atom_type in ("rule", "domain", "tool")
            for atom in self.reader.fetch(atom_type)
            for suffix in _domain_suffixes(atom.tags)
        })
        if not scenarios:
            return ""

        top_level = [scenario for scenario in scenarios if "." not in scenario]
        return top_level[0] if top_level else scenarios[0]

    def _select_atoms(self, atom_type: str, scenario: str) -> list[Atom]:
        atoms = self.reader.fetch(atom_type)
        return sorted(
            [atom for atom in atoms if _matches_scenario(atom.tags, scenario)],
            key=lambda atom: atom.id,
        )

    def _select_tools(self, scenario: str) -> list[ToolAtom]:
        tools = self.reader.fetch("tool")
        matching = [tool for tool in tools if isinstance(tool, ToolAtom) and _matches_scenario(tool.tags, scenario)]
        return sorted(matching, key=lambda tool: tool.id)

    def _load_user_traits(self, user_id: int | None) -> list[str]:
        if user_id is None or self.identity_session is None:
            return []

        statement = select(UserTraits.trait_id).where(UserTraits.user_id == user_id).order_by(UserTraits.trait_id)
        return list(self.identity_session.scalars(statement))


def compile_context(
    *,
    question: str,
    user_id: int | None,
    scenario: str | None = None,
    trigger: str = "user",
    session_state: SessionStateLike | None = None,
    reader: SLDBReader | None = None,
    identity_session: Session | None = None,
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None,
) -> dict[str, Any]:
    compiler = ContextCompiler(
        reader=reader or SLDBReader(),
        identity_session=identity_session,
        session_state_loader=session_state_loader,
    )
    return compiler.compile(
        question=question,
        user_id=user_id,
        scenario=scenario,
        trigger=trigger,
        session_state=session_state,
    )


def _serialize_atoms(atoms: list[Atom]) -> list[dict[str, str]]:
    return [{"id": atom.id, "body": atom.body} for atom in atoms]


def _matches_scenario(tags: list[str], scenario: str) -> bool:
    if not scenario:
        return False
    return any(_matches_domain_tag(tag, scenario) for tag in tags)


def _matches_domain_tag(tag: str, scenario: str) -> bool:
    normalized = tag.strip()
    prefix = "domain:"
    if not normalized.startswith(prefix):
        return False

    domain = normalized[len(prefix):]
    return domain == scenario or domain.startswith(f"{scenario}.")


def _domain_suffixes(tags: list[str]) -> list[str]:
    return [tag.split(":", 1)[1] for tag in tags if tag.startswith("domain:")]
