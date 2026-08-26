"""Compilador de contexto: navega SLDB + KGDB + SQL para producir CompiledDocument.

Doctrina de selección (ver KB-DOCTRINE.md):
  - Una KB = un negocio. El concepto viejo de "scenario == domain:<pizzeria>"
    (donde el escenario ERA el dominio y se usaba para filtrar átomos) ya NO
    aplica. Los átomos se seleccionan por su eje semántico (self:*,
    conversation:*, domain:*, user:traits.*) y se tratan según su ``atom_type``.
  - Como TODOS los átomos de la KB pertenecen al único negocio, el compilador
    trae TODOS los ``atom_type:domain`` y ``atom_type:rule`` sin filtrarlos por
    un scenario string. Esto incluye ``self:*`` (identidad/estilo/límites) y
    ``conversation:*`` (steps/strategy/fallback), que llevan ``atom_type`` de
    domain o rule y por eso entran naturalmente por tipo.
  - ``scenario`` se conserva solo como etiqueta informativa del negocio y como
    pista opcional para el enriquecimiento KGDB; NUNCA descarta átomos válidos.

Flujo:
  1. Resuelve scenario (etiqueta informativa; argumento -> session_state -> default)
  2. Selecciona atoms por ``atom_type`` en SLDB (domain, rule, tool)
  3. Resuelve traits del usuario contra SQL (user:traits.* del catálogo)
  4. [Opcional] Navega grafo KGDB para resolver nodo de flujo, transiciones, slots
  5. Compila a un CompiledDocument con facts, rules, tools, grounding + flujo
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

        # Doctrina nueva: una KB = un negocio. Todos los atom_type:domain y
        # atom_type:rule pertenecen a este único negocio. Se traen por atom_type
        # y luego se CLASIFICAN por eje semántico (self / conversation / domain)
        # para que el conversador arme su prompt sin hardcodear nada.
        raw_domain = self._find_atoms("domain")
        raw_rules = self._find_atoms("rule")
        tools = self._find_tools()
        user_traits = self._load_user_traits(user_id)

        persona = self._extract_persona(raw_domain + raw_rules)
        strategy = self._extract_by_tag(raw_rules, "conversation:strategy")
        fallback_text = self._extract_by_tag(raw_rules, "conversation:fallback")

        # domain_facts/rules quedan como grounding del NEGOCIO: se excluye lo que
        # ya viaja como persona/strategy/fallback (ejes self:* y conversation:*).
        domain_facts = self._grounding_only(raw_domain)
        rules = self._grounding_only(raw_rules)

        doc = CompiledDocument(
            scenario=resolved_scenario,
            question=question,
            user_traits=user_traits,
            domain_facts=domain_facts,
            rules=rules,
            tools=tools,
            persona=persona,
            strategy=strategy,
            fallback_text=fallback_text,
            is_empty=not domain_facts and not rules,
        )

        # Enriquecer con el diagrama de conversacion (KGDB), si hay grafo.
        # current_step viene del estado de sesion persistido en SQL (flow_node).
        if self.kgdb is not None:
            current_step = getattr(session_state, "flow_node", None)
            self._augment_from_kgdb(doc, resolved_scenario, current_step=current_step)

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
        """Etiqueta informativa del negocio (NO es un filtro de selección).

        Deriva un rótulo estable a partir de los tags ``domain:*`` presentes en
        la KB. Como una KB = un negocio, este valor solo describe la KB; los
        átomos ya se seleccionan por ``atom_type`` con independencia de él.
        """
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

    def _find_atoms(self, atom_type: str) -> list[dict[str, Any]]:
        """Selecciona TODOS los atoms de un ``atom_type`` de la KB del negocio.

        No se filtra por scenario: una KB = un negocio, así que todos los
        ``atom_type:domain`` y ``atom_type:rule`` son conocimiento válido del
        único negocio (incluye self:* y conversation:*). Se conservan los ``tags``
        para que el compilador pueda clasificar por eje semántico.
        """
        matched = self.reader.find(f"atom_type:{atom_type}")
        return sorted(
            [
                {
                    "id": m["id"],
                    "body": m.get("answer", ""),
                    "tags": m.get("tags", []),
                    "title": m.get("title") or m["id"],
                }
                for m in matched
            ],
            key=lambda x: x["id"],
        )

    # ── clasificacion por eje semantico (deshardcodeo) ────────────

    @staticmethod
    def _has_tag_prefix(atom: dict[str, Any], prefix: str) -> bool:
        return any(str(t).startswith(prefix) for t in atom.get("tags", []))

    @staticmethod
    def _has_tag(atom: dict[str, Any], tag: str) -> bool:
        return tag in atom.get("tags", [])

    def _extract_persona(self, atoms: list[dict[str, Any]]) -> dict[str, str]:
        """Arma la persona del agente desde los atoms ``self:*``.

        Devuelve un dict {faceta: body} donde faceta es whoami/estilo/limites/...
        derivado del tag ``self:<faceta>``. Reemplaza el prompt hardcodeado.
        """
        persona: dict[str, str] = {}
        for atom in atoms:
            for tag in atom.get("tags", []):
                tag = str(tag)
                if tag.startswith("self:"):
                    faceta = tag.split(":", 1)[1]
                    persona[faceta] = atom.get("body", "")
        return persona

    def _extract_by_tag(self, atoms: list[dict[str, Any]], tag: str) -> str:
        """Devuelve el body del primer atom que tenga ``tag`` (o cadena vacía)."""
        for atom in atoms:
            if self._has_tag(atom, tag):
                return atom.get("body", "")
        return ""

    def _grounding_only(self, atoms: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Filtra los atoms que son grounding del NEGOCIO (domain:*).

        Excluye self:* y conversation:* porque esos ya viajan como persona,
        strategy y fallback. Así el grounding que ve el conversador es solo el
        conocimiento del negocio, no la configuración del agente.
        """
        result = []
        for atom in atoms:
            if self._has_tag_prefix(atom, "self:") or self._has_tag_prefix(atom, "conversation:"):
                continue
            # Se preservan tags y title para que el orquestador arme el contexto
            # del turno SIN re-leer el store (brecha #2).
            result.append({
                "id": atom["id"],
                "body": atom.get("body", ""),
                "tags": atom.get("tags", []),
                "title": atom.get("title") or atom["id"],
            })
        return result

    def _find_tools(self) -> list[dict[str, Any]]:
        """Selecciona TODOS los tool atoms de la KB y devuelve su schema JSON."""
        matched = self.reader.find("atom_type:tool")
        tools = []
        for m in matched:
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

    def _augment_from_kgdb(
        self,
        doc: CompiledDocument,
        scenario: str,
        current_step: str | None = None,
    ) -> None:
        """Enriquece el CompiledDocument con el diagrama de conversacion del KGDB.

        El grafo generado desde SLDB es tag-centrico: el diagrama de conversacion
        vive en la jerarquia ``conversation:steps.*``. Este metodo:
          1. determina el step actual (viene del SessionState via ``current_step``,
             o cae al onboarding si existe, o al primer step disponible),
          2. expone los steps hermanos como transiciones permitidas,
          3. resuelve los documentos que groundean el step contra SLDB.
        """
        if self.kgdb is None:
            return

        steps = self.kgdb.steps_under("conversation:steps")
        if not steps:
            return

        # Step actual: el que trae la sesion, si es valido; si no, onboarding; si
        # no existe onboarding, el primer step del diagrama.
        active = current_step if current_step in steps else None
        if active is None:
            onboarding = next((s for s in steps if s.endswith(".onboarding")), None)
            active = onboarding or steps[0]

        doc.flow_node = active
        # Transiciones permitidas: los otros steps del diagrama (hermanos).
        doc.allowed_transitions = [s for s in steps if s != active]
        # Grounding: documentos etiquetados con el step actual (resueltos en SLDB).
        doc.grounding_atoms = self.kgdb.docs_for_tag(active)

    def _load_user_traits(self, user_id: int | None) -> list[str]:
        if user_id is None or self.identity_session is None:
            return []
        statement = select(UserTraits.trait_id).where(UserTraits.user_id == user_id).order_by(UserTraits.trait_id)
        return list(self.identity_session.scalars(statement))


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