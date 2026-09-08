"""Capa de negocio sobre la KB: lo que sldb/kgdb/pron NO deciden.

El acceso al store y al grafo es de pron (``World``/``Store``/``Graph``); aca
viven el contrato de runtime de los documentos (``doc``/``docs_by_type``/
``docs_by_tag``), el cruce con SQL (traits), la exploracion que usa el
ruteador, y las operaciones offline de mantenimiento de la KB (propose,
promote, organize, reflect).
"""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

import yaml
from sldb.cli.model_utils import resolve_model_ref
from pron.embedder import DocumentIndex, Embedder, Matcher
from pron.graph import Graph, bare, kind, tag_id
from pron.world import World
from sldb.store.io import load_documents_index

from kb_agent.knowledge.embedder import default_embedder
from kb_agent.knowledge.flow import ConversationFlow
from kb_agent.knowledge.world import open_world, refresh_world
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kb_agent.models.knowledge import DomainAtom, RuleAtom, ToolAtom, TraitAtom
from kb_agent.models.knowledge import ConversationStep, SelfDeclaration, StyleGuide
from kb_agent.models.knowledge import CapabilityBoundary, StrategyRule, FallbackRule
from kb_agent.models.knowledge import GateCriterion
from kb_agent.models_sql.identity import Base, Users, UserTraits

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
    "gate": GateCriterion,
}

ALL_MODELS = list(MODEL_MAP.values())
EXCLUDED_ROUTE_NAMESPACES = {"type", "workspace", "source"}


@dataclass(frozen=True)
class _DocRecord:
    """Documento resuelto del store, en la forma que ya esperaban los
    callers existentes de ``KnowledgeOperations._find_records()`` (p.ej.
    ``frontends/viz/export_graph.py::_load_atoms``, que llama al método
    "privado" directamente): ``.kind`` (siempre ``"doc"``, ya que
    ``_find_records`` solo devuelve documentos), ``.name``, ``.model_name``,
    ``.path``, ``.semantic`` (tags) y ``.payload`` (ya extraído, sin volver
    a leer/parsear el ``.md``).

    Es una vista liviana sobre ``sldb.store.query_engine.models.RuntimeDocument``
    (la fuente real, vía ``load_runtime_documents``), no una reimplementación:
    solo renombra/expone los campos que los callers de este módulo ya usaban
    cuando ``_find_records`` devolvía ``SearchRecord`` de
    ``sldb.cli.commands.find``.
    """

    kind: str
    name: str
    model_name: str
    path: str
    semantic: list[str]
    payload: dict[str, Any]


def derive_path(kb_root: Path, atom_id: str, tags: list[str]) -> Path:
    """Derive the destination path for an atom from its first significant tag.

    Tags whose namespace is ``type``, ``workspace``, or ``source`` are ignored,
    regardless of whether they use ``:`` or ``.`` as namespace separator.
    When no significant tag is present, the atom remains in the flat
    ``<kb>/atoms/`` fallback directory.
    """
    for tag in tags:
        if not isinstance(tag, str):
            continue
        stripped = tag.strip()
        if not stripped:
            continue
        namespace = stripped.split(":", 1)[0].split(".", 1)[0]
        if namespace in EXCLUDED_ROUTE_NAMESPACES:
            continue
        route = stripped.replace(":", "/").replace(".", "/").strip("/")
        if route:
            return kb_root / route / f"{atom_id}.md"
    return kb_root / "atoms" / f"{atom_id}.md"


class KnowledgeOperations:
    """Operations layer for the knowledge CLI.

    Wraps SLDB, KGDB, and SQL access into semantic commands.

    El embedder (jina, ~1 min de carga en frío) se cachea por INSTANCIA en
    ``self._embedder_cache`` (ver ``_embedder``). El orquestador/runtime debe
    crear UNA instancia de esta clase y reutilizarla para todo el proceso en
    vez de instanciarla por request.
    """

    def __init__(
        self, kb_root: str | Path, db_url: str | None = None, pythonpath: str | None = None, *,
        world: World | None = None, embedder: Embedder | None = None, embed_model: str | None = None,
    ) -> None:
        self._kb_root = Path(kb_root).resolve()
        self._pythonpath = pythonpath or str(self._kb_root.parent)
        #: El mundo de pron: UNICA puerta al store (documentos) y al grafo
        #: tipado (aristas de kgdb). Se abre una vez por proceso; el grafo se
        #: reconstruye solo cuando cambian los hashes de los modelos.
        self.world: World = world or open_world(self._kb_root, self._pythonpath)
        self._store_path = self.world.store.sp
        # SQL session for user traits and session state
        self._db_url = db_url
        self._engine: Any = None
        self._SessionLocal: Any = None
        self._flow: ConversationFlow | None = None
        #: Puerto de embeddings (``pron.embedder.Embedder``). Inyectable (tests);
        #: si no, fastembed en espanol, cargado perezosamente en ``_embedder``.
        self._embedder_cache: Embedder | None = embedder
        self._embed_model = embed_model
        self._doc_index: DocumentIndex | None = None
        # Se pone en True tras avisar (una vez) que la KB no tiene embeddings.
        self._warned_no_embeddings = False

    @property
    def kb_root(self) -> Path:
        return self._kb_root

    @property
    def graph(self) -> Graph:
        """El grafo tipado de la KB, fresco (se reconstruye si los modelos cambiaron)."""
        if refresh_world(self.world):
            self._flow = None
        return self.world.graph

    @property
    def flow(self) -> ConversationFlow:
        """Vista del diagrama de conversacion sobre ``graph``."""
        graph = self.graph
        if self._flow is None or self._flow.graph is not graph:
            self._flow = ConversationFlow(graph)
        return self._flow

    # ── helpers ────────────────────────────────────────────────

    def _lazy_sql(self) -> None:
        if self._engine is not None:
            return
        if not self._db_url:
            self._db_url = f"sqlite:///{self._kb_root / '.knowledge.db'}"
        self._engine = create_engine(self._db_url)
        self._SessionLocal = sessionmaker(bind=self._engine)

    def _invalidate_cache(self) -> None:
        """Toda operacion que ESCRIBE documentos (``propose``, ``promote``,
        ``organize``) invalida la lectura cacheada del store de pron y la vista
        del diagrama, para que una lectura posterior en el MISMO proceso vea
        los cambios."""
        self.world.store.invalidate()
        self._flow = None
        self._doc_index = None

    def _find_records(self) -> list[_DocRecord]:
        """Todos los documentos trackeados del store, resueltos, via ``pron.Store``
        (que cachea ``load_runtime_documents`` e invalida en cada escritura)."""
        return [
            _DocRecord(
                kind="doc", name=d.name, model_name=d.model_name, path=d.path,
                semantic=list(d.semantic_tags or []), payload=d.payload,
            )
            for d in self.world.store.docs()
        ]

    # ── runtime: acceso al store (unico dueno) ─────────────────
    #
    # El runtime (kb_agent) lee la KB SOLO por aca. Antes tenia su propio
    # lector, ``kb_agent/knowledge/sldb_reader.py::SLDBReader``, que volvia a
    # llamar a ``load_runtime_documents`` sobre el MISMO store: dos parseos y
    # dos caches por proceso que nadie sincronizaba.
    #
    # OJO con el contrato de ``tags``, que es lo unico que distingue estos dos
    # metodos de ``_read_doc``:
    #
    #   ``_read_doc``  -> contrato de EDICION. ``payload["tags"]`` son los tags
    #                     crudos del frontmatter, porque ``promote()`` los
    #                     reasigna y los reescribe al ``.md``. Meterle aca los
    #                     tags derivados del modelo escribiria
    #                     ``type.knowledge.rule`` dentro del archivo.
    #   ``doc``/``docs_by_type`` -> contrato de RUNTIME, de solo lectura.
    #                     ``tags`` son los ``semantic_tags`` del store: la union
    #                     del ``__semantics__`` de la clase
    #                     (``type.knowledge.<tipo>``, ``workspace.knowledge``) y
    #                     los del frontmatter. El compilador DEPENDE de esa
    #                     union: ``ContextCompiler._tipo_for_doc`` deriva el
    #                     tipo del tag ``type.knowledge.*``, que no existe en el
    #                     frontmatter de ningun atom.

    @staticmethod
    def _runtime_payload(record: "_DocRecord") -> dict[str, Any]:
        """Payload de un documento en el contrato de runtime (ver bloque arriba)."""
        payload = dict(record.payload or {})
        payload["id"] = record.name
        payload["tags"] = list(record.semantic or [])
        payload["path"] = str(record.path) if record.path else None
        return payload

    def docs_by_type(self, atom_type: str) -> list[dict[str, Any]]:
        """Atoms de un modelo tipado, via el eje ``type.knowledge.<atom_type>``.

        Pertenencia EXACTA al set de tags, que es lo que hace sldb
        (``SemanticEngine.get_semantic``). El lector viejo comparaba con
        ``term in tag`` (substring): con la taxonomia actual da lo mismo, pero
        un tag nuevo que contuviera a otro como prefijo lo habria hecho
        seleccionar de mas en silencio.
        """
        tag = f"type.knowledge.{atom_type}"
        return [
            self._runtime_payload(r) for r in self._find_records()
            if tag in (r.semantic or [])
        ]

    def docs_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Atoms que llevan ``tag``, o un hijo suyo en la jerarquia semantica.

        Match = pertenencia exacta al set de ``semantic_tags``, o descendencia
        por punto (``domain:medicamentos`` trae ``domain:medicamentos.sedanil``),
        que es como sldb arma el DAG (``store/semantic_tags.py::_prefix_edges``
        parte los tags por ``.``).

        NO es substring, a diferencia del ``SLDBReader.find`` que reemplaza:
        con ``term in tag``, buscar ``user:specialty.psiquiatria`` habria
        traido tambien ``user:specialty.psiquiatria_infantil``, en silencio.
        """
        prefix = f"{tag}."
        return [
            self._runtime_payload(r) for r in self._find_records()
            if any(t == tag or t.startswith(prefix) for t in (r.semantic or []))
        ]

    def doc(self, atom_id: str) -> dict[str, Any] | None:
        """Payload resuelto de un atom por id, en el contrato de runtime."""
        for r in self._find_records():
            if r.name == atom_id:
                return self._runtime_payload(r)
        return None

    def _read_doc(self, atom_id: str) -> dict[str, Any] | None:
        """Payload completo de un documento por id, contrato de EDICION (tags crudos
        del frontmatter), mas ``_model``/``_path``. Devuelve un dict NUEVO: los
        callers (``promote``) lo mutan antes de reescribirlo."""
        for doc in self._find_records():
            if doc.name != atom_id:
                continue
            doc_path = self._kb_root / doc.path
            model_cls = next((m for m in ALL_MODELS if m.__name__ == doc.model_name), None)
            if model_cls is None:
                return {"id": atom_id, "raw_path": str(doc_path)}
            payload = dict(doc.payload)
            payload["_model"] = model_cls.__name__
            payload["_path"] = str(doc_path)
            return payload
        return None

    # ── embeddings: pron.DocumentIndex (vectores en <kb>/.pron/, fuera de git) ──
    # Campos de texto por modelo, en orden de preferencia tras 'summary'.
    _EMBED_TEXT_FIELDS = (
        "summary", "answer", "statement", "description",
        "instructions", "restriction", "fallback_message",
        "tone", "goal", "title",
    )
    #: Modelos que NO llevan embedding por diseno: el encuadre de los agentes
    #: (``AgentFraming``, rol router/gate) no se recupera por similitud, se
    #: carga por rol. Contarlos como "sin vector" seria un falso positivo.
    _EMBEDDINGLESS_BY_DESIGN = {"AgentFraming"}

    def _embedder(self) -> Embedder | None:
        """El puerto de embeddings del proceso, cargado una vez por instancia.
        ``None`` si fastembed no esta instalado: el indice cae a difflib."""
        if self._embedder_cache is None:
            try:
                import fastembed  # noqa: F401
            except ImportError:
                logger.warning("fastembed no disponible: la similitud cae a difflib (pron.DocumentIndex)")
                return None
            self._embedder_cache = default_embedder(self._kb_root, self._embed_model)
        return self._embedder_cache

    def document_index(self) -> DocumentIndex:
        """El indice de documentos de la KB, en ``<kb>/.pron/docs.<embedder>.json``."""
        if self._doc_index is None:
            matcher = Matcher(self._embedder())
            safe_id = matcher.id().replace("/", "_").replace(":", "_")
            self._doc_index = DocumentIndex(matcher, self.world.derived_dir / f"docs.{safe_id}.json")
        return self._doc_index

    def _embed_text(self, payload: dict[str, Any]) -> str:
        for field in self._EMBED_TEXT_FIELDS:
            val = payload.get(field)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    def _embeddable_records(self) -> list[_DocRecord]:
        names = {m.__name__ for m in ALL_MODELS} - self._EMBEDDINGLESS_BY_DESIGN
        return [r for r in self._find_records() if r.model_name in names]

    def _embed_items(self) -> list[tuple[str, str, str]]:
        """``(id, hash_c, texto)`` por documento embebible; el hash viene del indice de
        documentos de sldb, asi un re-indexado solo embebe lo que cambio."""
        hashes: dict[str, str] = {}
        store = self.world.store
        for model in {r.model_name for r in self._embeddable_records()}:
            m_idx = store.models_index(model)
            for d in load_documents_index(store.project_root / m_idx.documents_index).documents:
                hashes[d.name] = d.hash_c
        items = []
        for r in self._embeddable_records():
            text = self._embed_text(r.payload or {})
            if text:
                items.append((r.name, hashes.get(r.name, ""), text))
        return items

    def index_embeddings(self) -> dict[str, Any]:
        """(Re)indexa la KB: embebe solo los documentos cuyo hash cambio."""
        stats = dict(self.document_index().index(self._embed_items()))
        stats["embedder"] = self.document_index().embedder_id
        stats["total"] = len(self.document_index().keys())
        return stats

    def audit_embeddings(self) -> dict[str, Any]:
        """Documentos embebibles que faltan en el indice (``ok=False`` si hay alguno).
        Es la guarda para el defecto invisible: una KB sin indice sigue
        respondiendo (difflib) sin que nada falle desde afuera."""
        indexed = set(self.document_index().keys())
        records = self._embeddable_records()
        missing = [{"id": r.name, "model": r.model_name} for r in records if r.name not in indexed]
        by_design = sum(1 for r in self._find_records() if r.model_name in self._EMBEDDINGLESS_BY_DESIGN)
        return {
            "kb": self._kb_root.name,
            "total": len(records),
            "with_embedding": len(records) - len(missing),
            "embeddingless_by_design": by_design,
            "missing": missing,
            "ok": not missing,
        }

    # ── offline: promote ────────────────────────────────────────

    def promote(self, atom_id: str) -> dict[str, Any]:
        """Promueve un atom propuesto: cambia status:proposed → status:active."""
        payload = self._read_doc(atom_id)
        if payload is None:
            raise ValueError(f"Atom '{atom_id}' not found")

        model_name = payload.get("_model", "")
        model_cls = next((m for m in ALL_MODELS if m.__name__ == model_name), None)
        if model_cls is None:
            raise ValueError(f"Unknown model '{model_name}' for atom {atom_id}")

        tags = payload.get("tags", [])
        if "status:proposed" not in tags:
            return {"id": atom_id, "status": "already_active", "message": "atom is not proposed"}

        # Replace proposed with active
        new_tags = [t for t in tags if t != "status:proposed"]
        if "status:active" not in new_tags:
            new_tags.append("status:active")
        self.world.store.update_field(model_name, atom_id, "tags", new_tags)
        self._invalidate_cache()
        return {"id": atom_id, "status": "active", "old_tags": tags, "new_tags": new_tags}

# ── offline: reflect ────────────────────────────────────────

    def reflect(self, db_url: str | None = None) -> list[dict[str, Any]]:
        """Corre el Reflector: lee ChatHistory y propone atoms nuevos.

        Requiere SQLite con tabla chat_history poblada.
        """
        from kb_agent.reflector import (
            InMemoryCheckpointStore,
            ReflectorAtomGenerator,
            ReflectorBatchReaderJob,
        )
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        actual_db = db_url or self._db_url
        if not actual_db:
            raise ValueError("Se requiere --db para connectar a la base de datos SQL")

        engine = create_engine(actual_db)
        SessionLocal = sessionmaker(bind=engine)

        reader = ReflectorBatchReaderJob(SessionLocal, InMemoryCheckpointStore())
        rows = reader.run()

        generator = ReflectorAtomGenerator(
            kb_root=self._kb_root, pythonpath=self._pythonpath, knowledge=self,
            registry_root=Path(self._pythonpath),
        )
        generated = generator.generate(rows)

        return [
            {
                "atom_id": atom.atom_id,
                "atom_type": atom.atom_type,
                "path": str(atom.path),
                "normalized_text": atom.normalized_text,
                "count": atom.count,
            }
            for atom in generated
        ]

    def organize(self, dry_run: bool = False) -> dict[str, Any]:
        """Organize flat KB atoms into semantic directories derived from tags."""
        atoms_dir = self._kb_root / "atoms"
        if not atoms_dir.exists():
            return {"kb_root": str(self._kb_root), "dry_run": dry_run, "moves": [], "processed": 0}

        moves: list[dict[str, Any]] = []
        store = self.world.store
        records = {str(r.path): r for r in self._find_records() if r.path}
        for doc_path in sorted(atoms_dir.glob("*.md")):
            record = records.get(str(doc_path.relative_to(self._kb_root)))
            if record is None:
                raise ValueError(f"Document '{doc_path}' is not tracked in the store")
            atom_id = record.name
            tags = list((record.payload or {}).get("tags") or [])
            model_name = record.model_name

            destination = derive_path(self._kb_root, atom_id, tags)
            action = "move" if destination != doc_path else "keep"
            move_record = {
                "id": atom_id,
                "model": model_name,
                "source": str(doc_path),
                "destination": str(destination),
                "action": action,
                "tags": tags,
            }
            moves.append(move_record)

            if dry_run or destination == doc_path:
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            store.untrack(atom_id)
            shutil.move(str(doc_path), str(destination))
            store.track(destination, model_name, atom_id)

        if not dry_run and any(move["action"] == "move" for move in moves):
            self.world.refresh()
            self._invalidate_cache()

        return {
            "kb_root": str(self._kb_root),
            "dry_run": dry_run,
            "processed": len(moves),
            "moves": moves,
        }


    # ── runtime: similitud ─────────────────────────────────────────
    # Por debajo de este score, un resultado semántico se marca "weak": el
    # llamador (ruteador) decide si lo usa o no, en vez de que un corte
    # absoluto lo descarte antes de que compita en el ranking.
    WEAK_SCORE_THRESHOLD = 0.25

    def _ranked(self, query: str, threshold: float) -> list[tuple[str, float]]:
        """``[(id, score)]`` mejor primero, con el indice al dia (embebe solo lo que cambio)."""
        index = self.document_index()
        index.index(self._embed_items())
        if not index.keys():
            if not self._warned_no_embeddings:
                self._warned_no_embeddings = True
                logger.warning("KB en %s: indice de documentos vacio; no hay retrieval semantico.", self._kb_root)
            return []
        return index.rank(query, threshold=threshold)

    def semantic_search(self, query: str, threshold: float = 0.05) -> list[dict[str, Any]]:
        """Similitud entre la query y TODOS los documentos embebibles, sin filtrar por
        modelo: el ruteador puede meter cualquier documento al bundle si lo justifica.

        ``threshold`` no es un corte semántico duro: es un piso absoluto muy bajo
        (ruido de embedding, default 0.05). El ranking real lo decide el orden por
        score + el flag ``weak`` de ``explore_multi``.
        """
        by_name = {r.name: r for r in self._find_records()}
        results = []
        for name, score in self._ranked(query, threshold):
            r = by_name.get(name)
            if r is None:
                continue
            results.append({
                "id": name, "model": r.model_name, "score": round(score, 4),
                "tags": list(r.semantic or []), "path": r.path,
                "title": (r.payload or {}).get("title", ""),
            })
        return results

    def rank_among(self, query: str, ids: Sequence[str], k: int | None = None, threshold: float = 0.05) -> list[tuple[str, float]]:
        """``[(id, score)]`` solo para ``ids`` (p.ej. los TraitAtom candidatos del perfilador),
        mejor primero; los ids sin vector no aparecen."""
        wanted = set(ids)
        hits = [(name, score) for name, score in self._ranked(query, threshold) if name in wanted]
        return hits[:k] if k is not None else hits

    # ── runtime: explore multi-estrategia ─────────────────────────
    def explore_multi(
        self,
        query: str,
        semantic_threshold: float = 0.05,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Explore del ruteador: similitud contra la KB + hermanos por tag en el grafo.

        Devuelve el top-k (``max_results``) ordenado por score, SIN descartar
        por umbral absoluto: ``semantic_threshold`` es solo un piso mínimo de
        ruido. Cada resultado trae ``weak: bool`` (score < ``WEAK_SCORE_THRESHOLD``)
        para que el llamador decida si lo usa, y ``siblings`` (documentos que
        comparten un tag semantico, via el grafo).
        """
        merged = self.semantic_search(query, threshold=semantic_threshold)[:max_results]
        for item in merged:
            item["weak"] = item["score"] < self.WEAK_SCORE_THRESHOLD
            item["siblings"] = self.siblings(item["id"])[:3]
        top_score = merged[0]["score"] if merged else 0.0
        return {
            "query": query,
            "results": merged,
            "top_score": top_score,
            "results_count": len(merged),
            "is_empty": top_score == 0.0 or len(merged) == 0,
        }

    def document_vectors(self) -> dict[str, list[float]]:
        """``{id: vector}`` del indice al dia (para el visualizador)."""
        index = self.document_index()
        index.index(self._embed_items())
        return index.vectors()

    # ── navegacion del grafo (aristas tagged_as / semantic_parent de kgdb) ──
    #: ejes demasiado amplios para navegar (todo documento los lleva).
    _META_TAG_PREFIXES = ("type.", "workspace.")

    def _doc_node(self, atom_id: str) -> str | None:
        for r in self._find_records():
            if r.name == atom_id:
                return f"sldb://document/{r.model_name}:{atom_id}"
        return None

    @staticmethod
    def _doc_name(node_id: str) -> str:
        b = bare(node_id)
        return b.split(":", 1)[1] if ":" in b else b

    def tags_for_doc(self, atom_id: str, include_meta: bool = False) -> list[str]:
        node = self._doc_node(atom_id)
        if node is None:
            return []
        tags = [bare(t) for t in self.graph.targets(node, "tagged_as")]
        return sorted(t for t in tags if include_meta or not t.startswith(self._META_TAG_PREFIXES))

    def docs_for_tag(self, tag: str) -> list[str]:
        return sorted(self._doc_name(n) for n in self.graph.sources(tag_id(tag), "tagged_as") if kind(n) == "document")

    def siblings(self, atom_id: str) -> list[str]:
        """Documentos que comparten al menos un tag semantico (no meta) con este."""
        node = self._doc_node(atom_id)
        if node is None:
            return []
        return [self._doc_name(n) for n in self.graph.neighbors_via(node, "tagged_as", exclude_prefixes=self._META_TAG_PREFIXES)]

    def explore(
        self,
        tag: str | None = None,
        atom: str | None = None,
    ) -> dict[str, Any]:
        """Navegacion de la KB por el grafo tipado (tool del ruteador).

        Modes:
          - no args:      entry points (root tags + counts)
          - --tag <t>:    expand a tag (parent, children, docs)
          - --atom <id>:  neighborhood of a doc (its tags + sibling docs)
        """
        graph = self.graph
        if atom is not None:
            return {"mode": "atom", "atom": atom, "tags": self.tags_for_doc(atom), "siblings": self.siblings(atom)}
        if tag is not None:
            node = tag_id(tag)
            parent = graph.parent(node)
            return {
                "mode": "tag", "tag": tag,
                "parent": bare(parent) if parent else None,
                "children": sorted(bare(c) for c in graph.children(node)),
                "docs": self.docs_for_tag(tag),
            }
        roots = []
        for root in graph.roots("semantic_tag", "semantic_parent"):
            name = bare(root)
            roots.append({"tag": name, "children": sorted(bare(c) for c in graph.children(root)), "docs": self.docs_for_tag(name)})
        return {"mode": "root", "root_tags": roots}

    def show(self, atom_id: str) -> dict[str, Any] | None:
        """Show a complete atom by id."""
        payload = self._read_doc(atom_id)
        if payload is None:
            return None
        return payload

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

    def propose(self, model_name: str, body_yaml: str | dict[str, Any]) -> dict[str, Any]:
        """Crea un atom PROPUESTO (tags ``status:proposed`` + ``source:reflector``):
        una escritura de sldb por libreria (``Store.create``: render, roundtrip,
        track), en la ruta que derivan sus tags (``derive_path``)."""
        model_cls = MODEL_MAP.get(model_name)
        if model_cls is None:
            raise ValueError(f"Unknown model '{model_name}'. Valid: {', '.join(MODEL_MAP.keys())}")
        payload = yaml.safe_load(body_yaml) if isinstance(body_yaml, str) else dict(body_yaml)
        if not isinstance(payload, dict):
            raise ValueError("body must be a YAML/JSON dict")
        payload.setdefault("tags", [])
        for tag in ("status:proposed", "source:reflector"):
            if tag not in payload["tags"]:
                payload["tags"].append(tag)
        doc_id = payload.get("id", f"proposed-{model_name}")
        atom_path = derive_path(self._kb_root, doc_id, list(payload.get("tags") or []))
        self.world.store.create(model_cls.__name__, doc_id, payload, atom_path)
        self._invalidate_cache()
        return {
            "id": doc_id,
            "model": model_name,
            "path": str(atom_path),
            "status": "proposed",
            "source": "reflector",
        }
