"""Core operations for the knowledge CLI.

Wraps SLDB (atom access), KGDB (graph traversal), and SQL (session state, traits)
into semantic commands for agent consumption.
"""
from __future__ import annotations

import json
import shutil
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
from kb_agent.models.knowledge import GateCriterion
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

        records = self._find_records()
        stats = {"processed": 0, "skipped": 0, "errors": 0}
        vector: list[float] = []

        # Resolver model_cls por nombre de clase (case-insensitive).
        by_class = {cls.__name__.lower(): cls for cls in ALL_MODELS}

        for r in records:
            if r.kind != "doc":
                continue
            model_cls = by_class.get((r.model_name or "").lower())
            if model_cls is None:
                continue
            if not r.path:
                stats["skipped"] += 1
                continue

            doc_path = self._kb_root / r.path
            if not doc_path.exists():
                stats["skipped"] += 1
                continue

            try:
                payload = extract_model_data(model_cls, doc_path.read_text(encoding="utf-8"))
            except Exception:
                stats["errors"] += 1
                continue

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

        stats["dimension"] = len(vector) if vector else 0
        return stats

    # ── offline: index hierarchy ────────────────────────────────

    def index_hierarchy(self) -> dict[str, Any]:
        """Construye jerarquía enciclopédica en el semantic DAG.

        Para cada tag con namespacing por puntos (ej. conversation:steps.onboarding),
        deriva el padre (conversation:steps) y añade relación semantic_parent
        si el padre existe como tag.
        """
        from sldb.store.io import load_store_index, save_store_index, load_models_index, save_models_index
        from sldb.store.layout import store_exists
        import yaml

        if not store_exists(self._store_path):
            return {"error": "No store at " + str(self._store_path)}

        store_idx = load_store_index(self._store_path)
        root = self._store_path.parent

        # Leer semantic_dag actual
        dag_path = self._store_path / "runtime" / "semantic_dag.yaml"
        if not dag_path.exists():
            return {"error": "semantic_dag.yaml not found"}

        raw = yaml.safe_load(dag_path.read_text(encoding="utf-8")) or {}
        nodes = raw.get("nodes", []) or []
        equivalences = raw.get("equivalences", {}) or {}

        # Colectar todos los tags existentes
        existing_tags = set()
        for node in nodes:
            nid = str(node.get("id", "")).strip()
            if nid and nid.startswith("sldb://semantic_tag/"):
                existing_tags.add(nid)

        # Derivar jerarquía: si un tag tiene puntos, truncar al último
        # conversation:steps.onboarding → conversation:steps
        new_edges = 0
        for tag_node in sorted(existing_tags):
            tag = tag_node.replace("sldb://semantic_tag/", "", 1)
            parts = tag.split(":", 1)
            if len(parts) != 2:
                continue
            namespace, value = parts[0], parts[1]
            if "." not in value:
                continue

            # Parent: truncar último segmento
            parent_value = value.rsplit(".", 1)[0]
            parent_tag = f"{namespace}:{parent_value}"
            parent_node = f"sldb://semantic_tag/{parent_tag}"

            if parent_node not in existing_tags:
                continue

            # Verificar si ya existe la relación semantic_parent
            already = False
            for node in nodes:
                if str(node.get("id", "")).strip() == tag_node:
                    if parent_node in [str(p).strip() for p in (node.get("parents", []) or [])]:
                        already = True
                    break

            if not already:
                for node in nodes:
                    if str(node.get("id", "")).strip() == tag_node:
                        node.setdefault("parents", []).append(parent_node)
                        new_edges += 1
                        break

        if new_edges > 0:
            raw["nodes"] = nodes
            dag_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")

        return {"tags": len(existing_tags), "new_parent_relations": new_edges}

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
            kb_root=self._kb_root,
            store_name=".sldb",
            output_dir=self._kb_root / "atoms",
            pythonpath=self._pythonpath,
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
            self._embedder_cache = TextEmbedding(
                model_name=self.EMBED_MODEL,
                cache_dir=str(self._kb_root / ".embedding_cache"),
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

    def _semantic_search(self, query: str, threshold: float = 0.05) -> list[dict[str, Any]]:
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

        records = self._find_records()
        results = []
        for r in records:
            if r.kind != "doc":
                continue
            doc = self._read_doc(r.name)
            if not doc:
                continue
            emb = doc.get("embedding")
            if not emb or not isinstance(emb, list) or len(emb) < 2:
                continue
            score = self._cosine_sim(qv, [float(v) for v in emb])
            if score < threshold:
                continue
            results.append({
                "id": r.name,
                "model": r.model_name,
                "score": round(score, 4),
                "tags": list(r.semantic or []),
                "path": r.path,
                "title": doc.get("title", ""),
            })
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

        records = self._find_records()
        results = []
        seen = set()
        for r in records:
            if r.kind != "doc":
                continue
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
        semantic = self._semantic_search(query, threshold=semantic_threshold)
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

        kgdb_enriched = []
        try:
            kgdb = self._kgdb()
            for item in merged:
                siblings = kgdb.sibling_docs(item["id"])[:3]
                item["siblings"] = siblings
                kgdb_enriched.append(item)
        except Exception:
            kgdb_enriched = merged

        top_score = merged[0]["score"] if merged else 0.0
        return {
            "query": query,
            "results": merged,
            "top_score": top_score,
            "results_count": len(merged),
            "is_empty": top_score == 0.0 or len(merged) == 0,
        }


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
        atom_path = derive_path(self._kb_root, doc_id, list(payload.get("tags") or []))

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