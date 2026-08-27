"""App factory FastAPI del runtime (chat UI + editor de flujo + perfilado + Twilio).

Cada turno pasa por: SLDBReader -> ContextCompiler (SLDB+KGDB) -> RouterStateMachine
-> policy decide_turn -> Conversador (LLM) -> Tool dispatcher (registry) -> Perfilador.

Endpoints:
  POST /api/chat                       -> corre un turno, devuelve el turno enriquecido
  POST /webhooks/twilio                -> canal WhatsApp/SMS (TwiML), valida firma
  GET  /api/atom/{id}                  -> devuelve un atom del store SLDB
  GET  /api/config                     -> config publica del negocio (marca, greeting, modelo)
  GET  /api/flow                       -> grafo de ConversationStep del store (JSON en vivo)
  GET  /api/profiles                   -> UserTraits(SQL) x TraitAtom(SLDB)
  GET  /api/taxonomy                   -> arbol taxonomico completo (familias x atoms)
  GET  /api/viz/graph                  -> grafo de atoms+embeddings (PCA 2D) del store en vivo
  GET  /api/health
  GET  /, /flow, /mindmap, /users (+ redirects legacy) -> UIs estaticas

La app NO instancia nada al importar el modulo: ``create_app`` recibe (o
construye desde ``project.config.yaml``) el orquestador y lo deja en
``app.state``. Asi los tests levantan la app con DB temporal y LLM inyectado.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from kb_agent.models_sql.identity import Users, UserTraits
from kb_agent.models_sql.session import ChatHistory
from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import ProjectConfig, load_project_config

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDITOR_DIR = PROJECT_ROOT / "frontends" / "flow_editor"
PROFILING_DIR = PROJECT_ROOT / "frontends" / "profiling"
TAXONOMY_DIR = PROJECT_ROOT / "frontends" / "taxonomy"
VIZ_DIR = PROJECT_ROOT / "frontends" / "viz"
SHARED_DIR = PROJECT_ROOT / "frontends" / "shared"

UI_CHANNEL = "ui"


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    scenario: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    turn: dict


def _external_id(session_id: str) -> str:
    """Mapea session_id de la UI a un external_id estable del orquestador."""
    return f"{UI_CHANNEL}:{session_id}"


def to_ui_turn(turn_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Adapta la salida de handle_turn al contrato que consume la UI.

    El bundle justificado del turno (doctrina 1.3: ~12 documentos con motivo,
    no "todo domain+rule" con score 1.0 hardcodeado) va DENTRO de ``context``,
    no como bloque ``decisions`` aparte:
      - cada ``context.items[i]`` ya trae ``motivo`` y el ``score`` real
        (``None`` si entro por piso de seguridad/grounding/trait, sin
        similitud) -- eso es lo que consume el Turn Inspector para las
        cards que YA renderiza (mismo namespace, minimo diff en el JS).
      - ``context.bundle`` expone la lista completa del bundle (incluye
        entradas que no proyectan a domain_facts/rules, p.ej. un
        ConversationStep o un TraitAtom que entraron por similitud) para
        auditoria completa sin tener que cruzar con ``decisions.ruteador``.
    """
    context = raw.get("context", {}) or {}
    return {
        "turn_id": turn_id,
        "user_message": raw.get("question", ""),
        "assistant_message": raw.get("reply_text", ""),
        "kind": raw.get("kind"),
        "scenario": raw.get("scenario_effective"),
        "scenario_source": raw.get("scenario_source"),
        "state_trace": raw.get("state_trace", []),
        "flow_node": raw.get("flow_node"),
        "allowed_transitions": raw.get("allowed_transitions", []),
        "traits_after": raw.get("traits_after", []),
        "system_turn": raw.get("system_turn"),
        "context": {
            "context_id": f"ctx-{turn_id}",
            "scenario": context.get("scenario", ""),
            "atom_ids": context.get("atom_ids", []),
            "include_tags": context.get("include_tags", []),
            "items": context.get("items", []),
            "tools": context.get("tools", []),
            "user_traits": context.get("user_traits", []),
            "grounding_atoms": context.get("grounding_atoms", []),
            "is_empty": context.get("is_empty", False),
            "bundle": context.get("bundle", []),
        },
    }


def _tree_to_list(children: dict, parent_key: str) -> list[dict]:
    """Convierte arbol anidado a lista plana con depth."""
    out = []
    for name, node in sorted(children.items()):
        entry = {
            "name": name,
            "path": f"{parent_key}.{name}" if parent_key else name,
            "atoms": node.get("atoms", []),
            "children": _tree_to_list(node.get("children", {}), f"{parent_key}.{name}"),
        }
        out.append(entry)
    return out


def create_app(cfg: ProjectConfig | None = None, orchestrator: Orchestrator | None = None) -> FastAPI:
    cfg = cfg or load_project_config()
    if orchestrator is None:
        cfg.chat_db.parent.mkdir(parents=True, exist_ok=True)
        orchestrator = Orchestrator.from_config(cfg)

    app = FastAPI(title=cfg.runtime_title)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.cfg = cfg
    app.state.orchestrator = orchestrator
    app.state.turn_counters = {}
    app.mount("/static", StaticFiles(directory=str(SHARED_DIR)), name="static")

    def _orch() -> Orchestrator:
        return app.state.orchestrator

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        if not req.message or not req.message.strip():
            raise HTTPException(status_code=400, detail="message vacio")

        session_id = req.session_id or uuid4().hex[:12]
        raw = _orch().handle_turn(
            external_id=_external_id(session_id),
            message=req.message,
            # Doctrina: una KB = un negocio. scenario NO filtra; es etiqueta opcional.
            scenario=req.scenario,
            channel=UI_CHANNEL,
        )
        counters: dict[str, int] = app.state.turn_counters
        counters[session_id] = counters.get(session_id, 0) + 1
        return ChatResponse(session_id=session_id, turn=to_ui_turn(f"t{counters[session_id]}", raw))

    @app.post("/webhooks/twilio")
    async def twilio_inbound(request: Request) -> Response:
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not token:
            raise HTTPException(status_code=503, detail="twilio not configured (TWILIO_AUTH_TOKEN)")
        form = {key: value for key, value in (await request.form()).items()}
        signature = request.headers.get("X-Twilio-Signature", "")
        if not RequestValidator(token).validate(str(request.url), form, signature):
            raise HTTPException(status_code=403, detail="invalid twilio signature")

        result = await run_in_threadpool(
            _orch().handle_turn,
            external_id=form.get("From", ""),
            message=(form.get("Body", "") or "").strip(),
        )
        twiml = MessagingResponse()
        twiml.message(result.get("reply_text") or result.get("reply") or "")
        return Response(str(twiml), media_type="application/xml")

    @app.get("/api/atom/{atom_id}")
    def get_atom(atom_id: str) -> dict:
        doc = _orch().reader.get_doc(atom_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"atom {atom_id} no encontrado")
        return {
            "atom_id": doc.get("id", atom_id),
            "title": doc.get("title") or atom_id,
            "body": doc.get("answer", ""),
            "tags": doc.get("tags", []),
            "five_wh_one_plus": doc.get("five_wh_one_plus"),
            "path": doc.get("path"),
        }

    @app.get("/api/config")
    def config() -> JSONResponse:
        """Config publica del negocio activo (marca, greeting, modelo) para las UIs."""
        return JSONResponse(cfg.to_public_dict())

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(BASE_DIR / "index.html"))

    @app.get("/flow")
    @app.get("/flow/")
    def flow_editor() -> FileResponse:
        return FileResponse(str(EDITOR_DIR / "index.html"))

    @app.get("/api/flow")
    @app.get("/conversation_flow_editor/flow.json")
    def flow_graph() -> JSONResponse:
        """Genera el grafo de ConversationStep del store en vivo."""
        from frontends.flow_editor.export_flow import export

        return JSONResponse(export(str(cfg.flow_kb_root)))

    @app.get("/mindmap")
    @app.get("/mindmap/")
    def taxonomy_explorer() -> FileResponse:
        return FileResponse(str(TAXONOMY_DIR / "index.html"))

    @app.get("/api/taxonomy")
    def taxonomy() -> JSONResponse:
        """Arbol taxonomico completo: familias -> subpaths -> atoms.

        Cada doc tiene un tag type.knowledge.{model_name}.
        Los tags con prefijo de su familia definen la jerarquia.
        """
        # tag type.knowledge.{model_name} -> (atom_type, family)
        # NOTA: nombres cortos del tag (step, domain, trait...), NO nombres de clase.
        MODEL_MAP = {
            "self": ("self", "self"),
            "style": ("style", "self"),
            "boundary": ("boundary", "self"),
            "tool": ("tool", "self"),
            "domain": ("domain", "domain"),
            "rule": ("rule", "domain"),
            "gate": ("gate", "gate"),
            "step": ("step", "conversation"),
            "fallback": ("fallback", "conversation"),
            "strategy": ("strategy", "conversation"),
            "trait": ("trait", "user"),
        }

        reader = _orch().reader
        families: dict[str, dict] = {f: {"name": f, "children": {}, "orphans": []}
                                     for f in ("self", "domain", "conversation", "gate", "user")}

        for doc in reader.find("type.knowledge."):
            tags: list[str] = doc.get("tags") or []
            type_tag = next((t for t in tags if t.startswith("type.knowledge.")), None)
            if not type_tag:
                continue
            model_name = type_tag.split(".", 2)[-1]
            mapping = MODEL_MAP.get(model_name)
            if not mapping:
                continue
            atype, fam = mapping
            atom_id = doc.get("id")
            entry = {
                "id": atom_id,
                "title": doc.get("title") or atom_id,
                "atom_type": atype,
                "summary": doc.get("summary"),
                "five_wh_one_plus": doc.get("five_wh_one_plus"),
                "tags": tags,
            }

            fam_tags = [t for t in tags if t.startswith(fam + ":")]
            if not fam_tags:
                families[fam]["orphans"].append(entry)
                continue

            for tag in fam_tags:
                path = tag[len(fam) + 1:]
                segments = path.split(".")
                node = families[fam]["children"]
                # navega por los segmentos, creando sub-nodos en la rama children
                for seg in segments[:-1]:
                    if seg not in node:
                        node[seg] = {"children": {}, "atoms": []}
                    node = node[seg]["children"]
                # ultimo segmento: coloca el atom en este nodo
                last = segments[-1]
                if last not in node:
                    node[last] = {"children": {}, "atoms": []}
                node[last]["atoms"].append(entry)

        result = {}
        for fam, data in families.items():
            result[fam] = {
                "children": _tree_to_list(data["children"], fam),
                "orphans": data["orphans"],
                "label": fam,
            }
        return JSONResponse(result)

    @app.get("/api/tools")
    def tools() -> JSONResponse:
        """Lista de ToolAtoms de la KB activa (nombre, schema, description, tool_id)."""
        reader = _orch().reader
        tools_list: list[dict] = []
        for doc in reader.find("type.knowledge.tool"):
            tool_id = doc.get("id")
            if not tool_id:
                continue
            tools_list.append({
                "tool_id": tool_id,
                "name": doc.get("title") or tool_id,
                "description": doc.get("description", ""),
                "schema": doc.get("function_schema", {}),
                "tags": doc.get("tags", []),
            })
        return JSONResponse(tools_list)

    @app.get("/users")
    @app.get("/users/")
    def profiling_viewer() -> FileResponse:
        return FileResponse(str(PROFILING_DIR / "index.html"))

    @app.get("/api/viz/graph")
    def viz_graph(edge_threshold: float | None = None, max_edges_per_node: int | None = None) -> JSONResponse:
        """Grafo de atoms+embeddings (PCA 2D, similitud coseno) de la KB activa.

        Nunca lee los JSON estaticos historicos: se recalcula del store en vivo
        (misma doctrina que /api/flow y /api/taxonomy). Cachea por (kb_root,
        edge_threshold, max_edges_per_node) en app.state porque el calculo
        (embeddings + PCA + similitud) no es instantaneo.
        """
        from frontends.viz.export_graph import (
            DEFAULT_EDGE_THRESHOLD,
            DEFAULT_MAX_EDGES_PER_NODE,
            build_graph,
        )

        threshold = DEFAULT_EDGE_THRESHOLD if edge_threshold is None else edge_threshold
        max_edges = DEFAULT_MAX_EDGES_PER_NODE if max_edges_per_node is None else max_edges_per_node

        cache: dict[tuple[str, float, int], dict] = getattr(app.state, "viz_cache", None) or {}
        key = (str(cfg.kb_root), threshold, max_edges)
        graph = cache.get(key)
        if graph is None:
            graph = build_graph(str(cfg.kb_root), pythonpath=str(PROJECT_ROOT), edge_threshold=threshold, max_edges_per_node=max_edges)
            cache[key] = graph
            app.state.viz_cache = cache

        return JSONResponse({"kb": cfg.name, **graph})

    OLD_ROUTES = {
        "/conversation_flow_editor": "/flow",
        "/taxonomy_explorer": "/mindmap",
        "/viz": "/mindmap",
        "/profiling_viewer": "/users",
    }

    def _redirect_factory(dest: str):
        async def _redirect() -> RedirectResponse:
            return RedirectResponse(url=dest, status_code=301)
        return _redirect

    for old_path, new_path in OLD_ROUTES.items():
        app.add_api_route(old_path, _redirect_factory(new_path), methods=["GET"])
        app.add_api_route(old_path + "/", _redirect_factory(new_path), methods=["GET"])

    @app.get("/api/profiles")
    def profiles() -> JSONResponse:
        """Perfil ampliado: cruza UserTraits (SQL) con TraitAtom (SLDB) + eventos + conversaciones."""
        engine = create_engine(f"sqlite:///{cfg.profiling_db}", future=True)
        Session = sessionmaker(bind=engine, future=True)

        users_out: list[dict] = []
        trait_ids: set[str] = set()
        try:
            with Session() as s:
                for u in s.query(Users).all():
                    rows = s.query(UserTraits).filter(UserTraits.user_id == u.id).all()
                    traits = []
                    for r in rows:
                        trait_ids.add(r.trait_id)
                        traits.append({
                            "trait_id": r.trait_id,
                            "confidence": r.confidence,
                            "source": r.source,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                        })
                    traits.sort(key=lambda t: t["confidence"], reverse=True)

                    # conversaciones del usuario
                    history_rows = s.query(ChatHistory).filter(
                        ChatHistory.user_id == u.id
                    ).order_by(ChatHistory.created_at.desc()).limit(20).all()
                    conversations = []
                    for h in history_rows:
                        conversations.append({
                            "session_id": f"hist-{h.id}",
                            "created_at": h.created_at.isoformat() if h.created_at else None,
                            "summary": (h.content[:80] if h.content else "") if h.role == "user" else "",
                            "role": h.role,
                            "n_turns": 1,
                            "result": "unknown",
                        })

                    users_out.append({
                        "user_id": u.id,
                        "external_id": u.external_id,
                        "channel": u.channel,
                        "traits": traits,
                        "traits_count": len(traits),
                        "total_turns": len(history_rows),
                        "last_active": history_rows[0].created_at.isoformat() if history_rows else None,
                        "created_at": u.created_at.isoformat() if hasattr(u, "created_at") and u.created_at else None,
                        "conversations": conversations,
                    })
        finally:
            engine.dispose()

        fichas: dict[str, dict] = {}
        for doc in _orch().reader.find("type.knowledge.trait"):
            tid = doc.get("id")
            if tid is None:
                continue
            fichas[tid] = {
                "id": tid,
                "title": doc.get("title") or tid,
                "description": doc.get("description", ""),
                "category": doc.get("category"),
                "tags": doc.get("tags", []),
            }
        missing = sorted(trait_ids - set(fichas.keys()))
        return JSONResponse({"users": users_out, "fichas": fichas, "missing_fichas": missing})

    @app.get("/api/events")
    def events(user_id: int | None = None) -> JSONResponse:
        """Serie temporal de eventos de un usuario."""
        if user_id is None:
            return JSONResponse({"events": []})
        engine = create_engine(f"sqlite:///{cfg.profiling_db}", future=True)
        Session = sessionmaker(bind=engine, future=True)
        events_list: list[dict] = []
        try:
            with Session() as s:
                user = s.query(Users).filter(Users.id == user_id).first()
                if not user:
                    return JSONResponse({"events": [], "user_id": user_id})

                # chats como eventos
                for h in s.query(ChatHistory).filter(
                    ChatHistory.user_id == user_id
                ).order_by(ChatHistory.created_at.asc()).all():
                    events_list.append({
                        "timestamp": h.created_at.isoformat() if h.created_at else None,
                        "kind": "chat",
                        "label": (h.content[:60] if h.content else "mensaje") if h.role == "user" else "respuesta",
                        "kind_label": h.role,
                    })

                # traits como eventos
                for t in s.query(UserTraits).filter(UserTraits.user_id == user_id).all():
                    events_list.append({
                        "timestamp": t.created_at.isoformat() if t.created_at else None,
                        "kind": "trait",
                        "label": t.trait_id,
                        "confidence": t.confidence,
                    })
        finally:
            engine.dispose()

        events_list.sort(key=lambda e: e.get("timestamp") or "")
        return JSONResponse({
            "events": events_list,
            "user_id": user_id,
        })

    @app.get("/api/history")
    def history(external_id: str) -> JSONResponse:
        """Historial cronologico de ChatHistory de un usuario (para precargar el chat)."""
        engine = create_engine(f"sqlite:///{cfg.profiling_db}", future=True)
        Session = sessionmaker(bind=engine, future=True)
        msgs: list[dict] = []
        try:
            with Session() as s:
                user = s.query(Users).filter(Users.external_id == external_id).first()
                if user:
                    for h in s.query(ChatHistory).filter(
                        ChatHistory.user_id == user.id
                    ).order_by(ChatHistory.created_at.asc()).all():
                        msgs.append({
                            "role": h.role,
                            "content": h.content,
                            "created_at": h.created_at.isoformat() if h.created_at else None,
                        })
        finally:
            engine.dispose()
        return JSONResponse({"external_id": external_id, "messages": msgs})

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "kb_root": str(cfg.kb_root), "model": _orch().model}

    return app
