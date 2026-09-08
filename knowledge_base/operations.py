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
from typing import Any

logger = logging.getLogger(__name__)

import yaml
from sldb.cli.model_utils import resolve_model_ref
from sldb.runtime.validation import render_model_markdown
from pron.graph import Graph, bare, kind, tag_id
from pron.world import World

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
MODEL_NAME_BY_ATOM_TYPE = {
    "domain": "DomainAtom",
    "rule": "RuleAtom",
    "tool": "ToolAtom",
    "trait": "TraitAtom",
    "step": "ConversationStep",
    "self": "SelfDeclaration",
    "style": "StyleGuide",
    "boundary": "CapabilityBoundary",
    "strategy": "StrategyRule",
    "fallback": "FallbackRule",
    "gate": "GateCriterion",
}


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

    def __init__(self, kb_root: str | Path, db_url: str | None = None, pythonpath: str | None = None, *, world: World | None = None) -> None:
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
        # Se pone en True tras avisar (una vez) que la KB no tiene embeddings.
        self._warned_no_embeddings = False

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

    # ── offline: index embeddings ───────────────────────────────

    EMBED_MODEL = "jinaai/jina-embeddings-v2-base-es"  # español, 768 dim

    # Campos de texto por modelo, en orden de preferencia tras 'summary'.
    _EMBED_TEXT_FIELDS = (
        "summary", "answer", "statement", "description",
        "instructions", "restriction", "fallback_message",
        "tone", "goal", "title",
    )

    def index_embeddings(self, model: str | None = None) -> dict[str, Any]:
        """Calcula embeddings offline para TODOS los modelos de la KB.

        Lee cada atom, computa embedding del summary (o el primer campo de texto
        disponible según el modelo) y escribe el vector al frontmatter.
        ``model`` reemplaza ``EMBED_MODEL``.
        """
        if model:
            self.EMBED_MODEL = model
            self._embedder_cache = None
        embedder = self._embedder()

        docs = self._find_records()
        stats = {"processed": 0, "skipped": 0, "errors": 0}
        vector: list[float] = []

        # Resolver model_cls por nombre de clase (case-insensitive).
        by_class = {cls.__name__.lower(): cls for cls in ALL_MODELS}

        for doc in docs:
            model_cls = by_class.get((doc.model_name or "").lower())
            if model_cls is None:
                continue

            doc_path = self._kb_root / doc.path
            payload = dict(doc.payload)

            # Texto a embedder: summary primero, luego el primer campo con contenido.
            text = ""
            for field in self._EMBED_TEXT_FIELDS:
                val = payload.get(field)
                if isinstance(val, str) and val.strip():
                    text = val.strip()
                    break
            if not text:
                stats["skipped"] += 1
                continue

            try:
                emb_list = list(embedder.embed([text]))
                if not emb_list:
                    stats["errors"] += 1
                    continue
                vector = [round(float(v), 6) for v in emb_list[0]]
            except Exception:
                stats["errors"] += 1
                continue

            # Escribir embedding al frontmatter
            payload["embedding"] = vector
            md = render_model_markdown(model_cls, payload)
            doc_path.write_text(md + "\n", encoding="utf-8")
            stats["processed"] += 1

        # Actualizar store. Los embeddings ya quedaron persistidos en los .md;
        # una falla del store (p.ej. store raíz mal configurado) NO debe abortar
        # el pipeline ni descartar el reporte de lo ya escrito.
        if stats["processed"]:
            try:
                self._run_sldb("stores", "update")
            except Exception as exc:
                stats["store_update_error"] = str(exc)

        if stats["processed"]:
            self._invalidate_cache()

        stats["dimension"] = len(vector) if vector else 0
        return stats

    #: Modelos que NO llevan embedding por diseno: el encuadre de los agentes
    #: (``AgentFraming``, rol router/gate) no se recupera por similitud, se
    #: carga por rol. Contarlos como "sin vector" seria un falso positivo.
    _EMBEDDINGLESS_BY_DESIGN = {"AgentFraming"}

    def audit_embeddings(self) -> dict[str, Any]:
        """Cuenta atoms sin vector en la KB, separando los que faltan de los que
        no llevan por diseno (``_EMBEDDINGLESS_BY_DESIGN``).

        Es la guarda para el defecto invisible: una KB entera sin vectores
        sigue respondiendo por fuzzy literal, asi que nada falla desde afuera
        (paso con knowledge_vitali, 50/50 atoms sin embedding). Devuelve
        ``ok=False`` si hay atoms que DEBERIAN tener vector y no lo tienen;
        pensado para un chequeo de arranque o job de CI (ver ``cli.py``).
        """
        total = 0
        with_embedding = 0
        by_design = 0
        missing: list[dict[str, str]] = []
        embeddable = {m.__name__ for m in ALL_MODELS}
        for r in self._find_records():
            if r.model_name not in embeddable:
                continue
            total += 1
            doc = self._read_doc(r.name)
            emb = doc.get("embedding") if doc else None
            has_emb = bool(emb) and isinstance(emb, list) and len(emb) >= 2
            if has_emb:
                with_embedding += 1
                continue
            if r.model_name in self._EMBEDDINGLESS_BY_DESIGN:
                by_design += 1
                continue
            missing.append({"id": r.name, "model": r.model_name})
        return {
            "kb": self._kb_root.name,
            "total": total,
            "with_embedding": with_embedding,
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
        payload["tags"] = new_tags

        doc_path = Path(payload["_path"])
        md = render_model_markdown(model_cls, payload)
        doc_path.write_text(md + "\n", encoding="utf-8")
        self._invalidate_cache()

        return {"id": atom_id, "status": "active", "old_tags": tags, "new_tags": payload["tags"]}

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

    # ── helper: sldb subprocess call ────────────────────────────

    def _run_sldb(self, *args: str) -> None:
        """Corre un comando sldb con el store y pythonpath correctos."""
        import subprocess
        from pathlib import Path
        # pythonpath debe apuntar al project root, no al parent del kb
        project_root = Path(__file__).resolve().parents[1]
        cmd = ["sldb", *args, "--store", str(self._store_path), "--pythonpath", str(project_root)]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60, cwd=project_root)

    def _load_frontmatter(self, doc_path: Path) -> dict[str, Any]:
        text = doc_path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"Document '{doc_path}' does not start with YAML frontmatter")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Document '{doc_path}' has invalid YAML frontmatter")
        data = yaml.safe_load(parts[1]) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Document '{doc_path}' frontmatter must be a mapping")
        return data

    def organize(self, dry_run: bool = False) -> dict[str, Any]:
        """Organize flat KB atoms into semantic directories derived from tags."""
        atoms_dir = self._kb_root / "atoms"
        if not atoms_dir.exists():
            return {"kb_root": str(self._kb_root), "dry_run": dry_run, "moves": [], "processed": 0}

        moves: list[dict[str, Any]] = []
        for doc_path in sorted(atoms_dir.glob("*.md")):
            frontmatter = self._load_frontmatter(doc_path)
            atom_id = str(frontmatter.get("id") or doc_path.stem)
            tags = list(frontmatter.get("tags") or [])
            atom_type = str(frontmatter.get("atom_type") or "").strip().lower()
            model_name = MODEL_NAME_BY_ATOM_TYPE.get(atom_type)
            if model_name is None:
                raise ValueError(f"Unknown atom_type '{atom_type}' in {doc_path}")

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
            shutil.move(str(doc_path), str(destination))
            self._run_sldb("docs", "untrack", atom_id)
            self._run_sldb("docs", "track", str(destination), "--model", model_name)

        if not dry_run and any(move["action"] == "move" for move in moves):
            self._run_sldb("stores", "update")
            self._invalidate_cache()

        return {
            "kb_root": str(self._kb_root),
            "dry_run": dry_run,
            "processed": len(moves),
            "moves": moves,
        }


    # ── runtime: embedder ─────────────────────────────────────────

    _embedder_cache: Any = None

    def _embedder(self):
        """Lazy embedder (fastembed, español), cacheado a nivel de INSTANCIA.

        Cargar ``jinaai/jina-embeddings-v2-base-es`` tarda ~1 minuto en frío.
        ``_embedder_cache`` se guarda en ``self`` (no es un singleton de
        módulo/clase: la asignación de abajo crea un atributo de instancia
        que oculta el ``None`` de clase), así que el costo de carga se paga
        una sola vez POR INSTANCIA de ``KnowledgeOperations``. El
        orquestador/runtime debe crear UNA instancia y reutilizarla para
        todas las llamadas a explore/explore_multi/index_embeddings dentro
        del mismo proceso; crear una instancia nueva por request vuelve a
        pagar el minuto de carga.
        """
        if self._embedder_cache is None:
            from fastembed import TextEmbedding
            # El modelo pesa ~615MB. Por defecto se cachea junto a la KB, pero
            # en un despliegue con almacenamiento efimero (Modal: la imagen es
            # inmutable y .embedding_cache esta excluido a proposito) hay que
            # apuntarlo a un volumen persistente o se re-descarga en cada
            # arranque en frio. EMBEDDING_CACHE_DIR permite eso sin tocar la KB.
            import os

            cache_dir = os.environ.get("EMBEDDING_CACHE_DIR") or str(
                self._kb_root / ".embedding_cache"
            )
            self._embedder_cache = TextEmbedding(
                model_name=self.EMBED_MODEL,
                cache_dir=cache_dir,
            )
        return self._embedder_cache

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    # Por debajo de este score, un resultado semántico se marca "weak": el
    # llamador (ruteador) decide si lo usa o no, en vez de que un corte
    # absoluto lo descarte antes de que compita en el ranking.
    WEAK_SCORE_THRESHOLD = 0.25

    def semantic_search(self, query: str, threshold: float = 0.05) -> list[dict[str, Any]]:
        """Busca por similitud coseno entre la query y los embeddings de TODOS los
        documentos, sin filtrar por modelo.

        El ruteador puede meter cualquier documento al bundle si lo justifica
        (traits, steps, tools, no solo domain/rule). Con el filtro anterior a
        DomainAtom/RuleAtom, "me da miedo la aguja" devolvia dos IME a 0.30 y
        descartaba trait-antonia-ansioso-aplicacion (0.396) y
        trait-antonia-primera-vez (0.349), que rankean #1 y #2.

        ``threshold`` ya NO es un corte semántico duro: es un piso absoluto
        muy bajo (ruido de embedding, default 0.05) para no arrastrar
        documentos sin ninguna relación. El ranking real (qué tan relevante
        es un resultado) lo decide el orden por score + el flag ``weak``,
        no este umbral. Ver ``explore_multi`` para el top-k relativo.
        """
        embedder = self._embedder()
        query_emb = list(embedder.embed([query]))[0]
        qv = [float(v) for v in query_emb]

        docs = self._find_records()
        results = []
        seen_any_embedding = False
        for r in docs:
            # El payload ya viene resuelto en el record (``_find_records`` lo
            # trae de ``load_runtime_documents``). Esto llamaba a
            # ``self._read_doc(r.name)``, que vuelve a escanear TODOS los
            # records por cada documento del loop: O(n^2) con cache fria, ~4
            # min sobre la KB real. ``embedding`` y ``title`` son lo unico que
            # se usaba de ahi, y los dos estan en ``r.payload``.
            payload = r.payload or {}
            emb = payload.get("embedding")
            if not emb or not isinstance(emb, list) or len(emb) < 2:
                continue
            seen_any_embedding = True
            score = self._cosine_sim(qv, [float(v) for v in emb])
            if score < threshold:
                continue
            results.append({
                "id": r.name,
                "model": r.model_name,
                "score": round(score, 4),
                "tags": list(r.semantic or []),
                "path": r.path,
                "title": payload.get("title", ""),
            })
        # Degradacion muda: si HABIA documentos pero NINGUNO tenia embedding,
        # el retrieval semantico no puede funcionar y el sistema cae al fuzzy
        # literal sin que nadie se entere (fue exactamente lo que paso con
        # knowledge_vitali: 50/50 atoms sin vector). Avisar una sola vez por
        # instancia -- no en cada consulta -- para no inundar el log.
        if docs and not seen_any_embedding and not self._warned_no_embeddings:
            self._warned_no_embeddings = True
            logger.warning(
                "KB en %s: ninguno de los %d documentos tiene embedding; el "
                "retrieval semantico esta degradado a fuzzy literal. Corre "
                "'python -m knowledge_base --kb %s index embeddings'.",
                self._kb_root,
                len(docs),
                self._kb_root.name,
            )
        return sorted(results, key=lambda x: x["score"], reverse=True)

    _FUZZY_STOPWORDS = {
        "me", "da", "es", "la", "de", "que", "en", "y", "el", "un",
        "una", "por", "con", "mi", "tu", "su", "lo", "se", "te", "le",
        "sus", "mis", "tus", "del", "al", "no", "si", "ya", "muy",
    }
    _FUZZY_ACCENTS = str.maketrans("áéíóúüñ", "aeiouun")

    @classmethod
    def _tokenize_query(cls, query: str) -> list[str]:
        """Tokeniza una query en español: minúsculas, sin tildes, sin stopwords cortas."""
        import re

        normalized = query.lower().translate(cls._FUZZY_ACCENTS)
        raw_tokens = re.findall(r"[a-z0-9]+", normalized)
        return [
            t for t in raw_tokens
            if len(t) >= 4 and t not in cls._FUZZY_STOPWORDS
        ]

    def _fuzzy_search(self, query: str) -> list[dict[str, Any]]:
        """Busca por fracción de tokens de la query presentes en title/tags/summary/answer.

        Tokeniza la query (minúsculas, sin tildes, sin stopwords cortas) y puntúa
        cada documento como (# tokens que matchean) / (# tokens de la query), en
        rango 0..1, comparable con el score semántico.
        """
        tokens = self._tokenize_query(query)
        if not tokens:
            return []

        docs = self._find_records()
        results = []
        seen = set()
        for r in docs:
            if r.name in seen:
                continue
            seen.add(r.name)

            tags = [t.lower().translate(self._FUZZY_ACCENTS) for t in (r.semantic or [])]
            tags_blob = " ".join(tags)

            doc = self._read_doc(r.name) or {}
            title = str(doc.get("title", "")).lower().translate(self._FUZZY_ACCENTS)
            summary = str(doc.get("summary", "")).lower().translate(self._FUZZY_ACCENTS)
            answer = str(doc.get("answer", "")).lower().translate(self._FUZZY_ACCENTS)
            anchors = [str(a).lower().translate(self._FUZZY_ACCENTS) for a in (doc.get("semantic_anchors") or [])]
            anchors_blob = " ".join(anchors)

            matched_where: set[str] = set()
            matched_tokens = 0
            for tok in tokens:
                hit = False
                if tok in tags_blob or tok in anchors_blob:
                    matched_where.add("semantic_tag")
                    hit = True
                if tok in title:
                    matched_where.add("title")
                    hit = True
                if tok in summary:
                    matched_where.add("summary")
                    hit = True
                if tok in answer:
                    matched_where.add("answer")
                    hit = True
                if hit:
                    matched_tokens += 1

            if matched_tokens == 0:
                continue

            score = matched_tokens / len(tokens)
            results.append({
                "id": r.name,
                "model": r.model_name,
                "score": round(score, 4),
                "match": "+".join(sorted(matched_where)),
                "tags": list(r.semantic or []),
                "path": r.path,
            })
        return results

    # ── runtime: explore multi-estrategia ─────────────────────────

    def explore_multi(
        self,
        query: str,
        semantic_threshold: float = 0.05,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Explore multi-estrategia: embeds query, busca por similitud + fuzzy + KGDB.

        Devuelve el top-k (``max_results``) ordenado por score, SIN descartar
        por umbral absoluto: ``semantic_threshold`` es solo un piso mínimo muy
        bajo para filtrar ruido de embedding (default 0.05), se mantiene en la
        firma por compatibilidad. Cada resultado trae ``weak: bool``
        (score < ``WEAK_SCORE_THRESHOLD``, hoy 0.25) para que el llamador
        (el ruteador) decida si lo usa, en vez de que un corte duro lo
        descarte antes de competir en el ranking.
        """
        semantic = self.semantic_search(query, threshold=semantic_threshold)
        fuzzy = self._fuzzy_search(query)

        seen = set()
        merged = []
        for item in semantic:
            seen.add(item["id"])
            merged.append(item)
        for item in fuzzy:
            if item["id"] not in seen:
                seen.add(item["id"])
                item["score"] = round(item["score"] * 0.85, 4)
                merged.append(item)

        for item in merged:
            item["weak"] = item["score"] < self.WEAK_SCORE_THRESHOLD

        merged.sort(key=lambda x: x["score"], reverse=True)
        merged = merged[:max_results]

        for item in merged:
            item["siblings"] = self.siblings(item["id"])[:3]
        top_score = merged[0]["score"] if merged else 0.0
        return {
            "query": query,
            "results": merged,
            "top_score": top_score,
            "results_count": len(merged),
            "is_empty": top_score == 0.0 or len(merged) == 0,
        }


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
