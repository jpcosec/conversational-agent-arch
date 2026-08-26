"""Core operations for the knowledge CLI.

Wraps SLDB (atom access), KGDB (graph traversal), and SQL (session state, traits)
into semantic commands for agent consumption.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from sldb.cli.commands.find import SearchRecord, iter_search_records, search_records
from sldb.runtime.validation import extract_model_data, render_model_markdown
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kb_agent.models.knowledge import DomainAtom, RuleAtom, ToolAtom, TraitAtom
from kb_agent.models.knowledge import ConversationStep, SelfDeclaration, StyleGuide
from kb_agent.models.knowledge import CapabilityBoundary, StrategyRule, FallbackRule
from kb_agent.models_sql.identity import Base, Users, UserTraits
from kb_agent.models_sql.session import SessionState

MODEL_MAP = {
    "domain": DomainAtom,
    "rule": RuleAtom,
    "tool": ToolAtom,
    "trait": TraitAtom,
    "step": ConversationStep,
    "self": SelfDeclaration,
    "style": StyleGuide,
    "boundary": CapabilityBoundary,
    "strategy": StrategyRule,
    "fallback": FallbackRule,
}

ALL_MODELS = list(MODEL_MAP.values())


class KnowledgeOperations:
    """Operations layer for the knowledge CLI.

    Wraps SLDB, KGDB, and SQL access into semantic commands.
    """

    def __init__(self, kb_root: str | Path, db_url: str | None = None, pythonpath: str | None = None) -> None:
        self._kb_root = Path(kb_root).resolve()
        self._store_path = self._kb_root / ".sldb"
        self._pythonpath = pythonpath or str(self._kb_root.parent)

        # SQL session for user traits and session state
        self._db_url = db_url
        self._engine: Any = None
        self._SessionLocal: Any = None

    # ── helpers ────────────────────────────────────────────────

    def _lazy_sql(self) -> None:
        if self._engine is not None:
            return
        if not self._db_url:
            self._db_url = f"sqlite:///{self._kb_root / '.knowledge.db'}"
        self._engine = create_engine(self._db_url)
        self._SessionLocal = sessionmaker(bind=self._engine)

    def _find_records(self) -> list[SearchRecord]:
        return list(iter_search_records(self._store_path, pythonpath=self._pythonpath))

    def _search(self, term: str, search_in: str = "semantic") -> list[dict[str, Any]]:
        records = self._find_records()
        matched = search_records(records, term, search_in=search_in)
        results = []
        for r in matched:
            if r.kind == "doc":
                results.append({
                    "id": r.name,
                    "model": r.model_name,
                    "path": r.path,
                    "semantic": list(r.semantic or []),
                })
        return results

    def _read_doc(self, atom_id: str) -> dict[str, Any] | None:
        """Read a complete document by id from any model."""
        records = self._find_records()
        for r in records:
            if r.kind == "doc" and r.name == atom_id:
                if not r.path:
                    return None
                doc_path = self._kb_root / r.path
                if not doc_path.exists():
                    return None

                model_name = (r.model_name or "").lower()
                model_cls = MODEL_MAP.get(model_name)
                if model_cls is None:
                    # try nested lookup
                    for m_name, m_cls in MODEL_MAP.items():
                        if m_cls.__name__.lower() == model_name:
                            model_cls = m_cls
                            break
                if model_cls is None:
                    return {"id": atom_id, "raw_path": str(doc_path)}

                try:
                    payload = extract_model_data(model_cls, doc_path.read_text(encoding="utf-8"))
                    payload["_model"] = model_cls.__name__
                    payload["_path"] = str(doc_path)
                    return payload
                except Exception as exc:
                    return {"id": atom_id, "raw_path": str(doc_path), "error": str(exc)}
        return None

    # ── commands ───────────────────────────────────────────────

    def _kgdb(self):
        """Lazy KGDB reader."""
        from kb_agent.ontologizador.kgdb_reader import KGDBReader
        return KGDBReader.from_sldb(self._store_path, pythonpath=self._pythonpath)

    def explore(
        self,
        tag: str | None = None,
        atom: str | None = None,
    ) -> dict[str, Any]:
        """Navigate the KB via the KGDB graph.

        Modes:
          - no args:      entry points (root tags + counts)
          - --tag <t>:    expand a tag (parent, children, docs)
          - --atom <id>:  neighborhood of a doc (its tags + sibling docs)

        Returns a navigation view for the agent to walk the graph.
        """
        try:
            kgdb = self._kgdb()
        except Exception as exc:
            return {"error": f"KGDB unavailable: {exc}"}

        if atom is not None:
            return {
                "mode": "atom",
                "atom": atom,
                "tags": kgdb.tags_for_doc(atom),
                "siblings": kgdb.sibling_docs(atom),
            }

        if tag is not None:
            return {
                "mode": "tag",
                "tag": tag,
                "parent": kgdb.parent_tag(tag),
                "children": kgdb.child_tags(tag),
                "docs": kgdb.docs_for_tag(tag),
            }

        # entry points: root tags with doc counts
        roots = []
        for root in kgdb.root_tags():
            roots.append({
                "tag": root,
                "children": kgdb.child_tags(root),
                "docs": kgdb.docs_for_tag(root),
            })
        return {
            "mode": "root",
            "root_tags": roots,
        }

    def show(self, atom_id: str) -> dict[str, Any] | None:
        """Show a complete atom by id."""
        payload = self._read_doc(atom_id)
        if payload is None:
            return None
        return payload

    def step_next(self, user_id: str) -> dict[str, Any]:
        """Get next valid conversation step from session state + KGDB.

        Reads flow_node from SQL SessionState, resolves against KGDB.
        Returns current_step, allowed_transitions, grounding_atoms, missing_slots.
        Gracefully handles missing SQL tables.
        """
        flow_node = None
        allowed_transitions = []
        grounding_atoms = []
        missing_slots = []

        # Try SQL session state
        try:
            self._lazy_sql()
            session = self._SessionLocal()
            try:
                user = session.query(Users).filter_by(external_id=user_id).first()
                if user is not None:
                    ss = session.query(SessionState).filter_by(user_id=user.id).first()
                    if ss is not None:
                        flow_node = ss.flow_node
                        if ss.flow_slots:
                            missing_slots = ss.flow_slots.get("missing_slots", [])
            finally:
                session.close()
        except Exception:
            # SQL not available, continue with KGDB-only
            pass

        # Try KGDB for transitions
        try:
            from kb_agent.ontologizador.kgdb_reader import KGDBReader

            kgdb = KGDBReader.from_sldb(self._store_path, pythonpath=self._pythonpath)

            if flow_node and kgdb.graph.has_node(flow_node):
                transitions = kgdb.get_next_transitions(flow_node)
                allowed_transitions = [t["to"] for t in transitions]
                grounding_atoms = kgdb.get_grounding_atoms(flow_node)
        except Exception:
            pass

        if flow_node is None:
            steps = self._search("conversation:steps", search_in="semantic")
            if steps:
                flow_node = steps[0]["id"]

        return {
            "flow_node": flow_node,
            "allowed_transitions": allowed_transitions,
            "grounding_atoms": grounding_atoms,
            "missing_slots": missing_slots,
        }

    def traits(self, user_id: str) -> list[dict[str, Any]]:
        """Load user traits from SQL and resolve against TraitAtom in SLDB.

        Returns: list of {trait_id, title, description, category, confidence}
        """
        try:
            self._lazy_sql()
            session = self._SessionLocal()
            try:
                user = session.query(Users).filter_by(external_id=user_id).first()
                if user is None:
                    return []

                user_traits = session.query(UserTraits).filter_by(user_id=user.id).all()
                results = []
                for ut in user_traits:
                    trait_doc = self._read_doc(ut.trait_id)
                    results.append({
                        "trait_id": ut.trait_id,
                        "title": trait_doc.get("title", ut.trait_id) if trait_doc else ut.trait_id,
                        "description": trait_doc.get("description", "") if trait_doc else "",
                        "category": trait_doc.get("category", "") if trait_doc else "",
                        "confidence": ut.confidence,
                        "source": ut.source,
                    })
                return results
            finally:
                session.close()
        except Exception:
            return []

    def self_context(self) -> dict[str, Any]:
        """Compile all self-declarations, style guides, and capability boundaries."""
        results = {
            "identity": [],
            "style": [],
            "boundaries": [],
        }

        # Use model_name from records rather than semantic search
        records = self._find_records()
        for r in records:
            if r.kind != "doc":
                continue
            if r.model_name == "SelfDeclaration":
                doc = self._read_doc(r.name)
                if doc:
                    results["identity"].append({
                        "id": r.name,
                        "statement": doc.get("statement", ""),
                        "tags": doc.get("tags", []),
                    })
            elif r.model_name == "StyleGuide":
                doc = self._read_doc(r.name)
                if doc:
                    results["style"].append({
                        "id": r.name,
                        "tone": doc.get("tone", ""),
                        "language_register": doc.get("language_register", ""),
                        "phrase_preferences": doc.get("phrase_preferences", ""),
                        "length_guidelines": doc.get("length_guidelines", ""),
                    })
            elif r.model_name == "CapabilityBoundary":
                doc = self._read_doc(r.name)
                if doc:
                    results["boundaries"].append({
                        "id": r.name,
                        "restriction": doc.get("restriction", ""),
                        "conditions": doc.get("conditions", ""),
                        "escalation": doc.get("escalation", ""),
                    })

        return results

    def context(self, user_id: str) -> dict[str, Any]:
        """Full current session context: steps + traits + self.

        One-shot for the Compiler agent to get everything it needs.
        """
        return {
            "step": self.step_next(user_id),
            "traits": self.traits(user_id),
            "self": self.self_context(),
        }

    def propose(self, model_name: str, body_yaml: str) -> dict[str, Any]:
        """Create a proposed atom (for the Reflector agent).

        Writes the atom with status: proposed metadata in frontmatter.
        Returns the created atom info.
        """
        model_cls = MODEL_MAP.get(model_name)
        if model_cls is None:
            raise ValueError(f"Unknown model '{model_name}'. Valid: {', '.join(MODEL_MAP.keys())}")

        payload = yaml.safe_load(body_yaml) if isinstance(body_yaml, str) else body_yaml
        if not isinstance(payload, dict):
            raise ValueError("body must be a YAML/JSON dict")

        payload.setdefault("tags", [])
        if "status:proposed" not in payload["tags"]:
            payload["tags"].append("status:proposed")
        if "source:reflector" not in payload["tags"]:
            payload["tags"].append("source:reflector")

        doc_id = payload.get("id", f"proposed-{model_name}")
        atom_path = self._kb_root / "atoms" / f"{doc_id}.md"

        md = render_model_markdown(model_cls, payload)
        atom_path.parent.mkdir(parents=True, exist_ok=True)
        atom_path.write_text(md + "\n", encoding="utf-8")

        return {
            "id": doc_id,
            "model": model_name,
            "path": str(atom_path),
            "status": "proposed",
            "source": "reflector",
        }