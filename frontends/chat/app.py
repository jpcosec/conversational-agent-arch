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
  GET  /api/health
  GET  /, /conversation_flow_editor, /profiling_viewer, /taxonomy_explorer -> UIs estaticas

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
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from kb_agent.models_sql.identity import Users, UserTraits
from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import ProjectConfig, load_project_config

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDITOR_DIR = PROJECT_ROOT / "frontends" / "flow_editor"
PROFILING_DIR = PROJECT_ROOT / "frontends" / "profiling"
TAXONOMY_DIR = PROJECT_ROOT / "frontends" / "taxonomy"

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
    """Adapta la salida de handle_turn al contrato que consume la UI."""
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

    @app.get("/conversation_flow_editor")
    @app.get("/conversation_flow_editor/")
    def flow_editor() -> FileResponse:
        return FileResponse(str(EDITOR_DIR / "index.html"))

    @app.get("/api/flow")
    @app.get("/conversation_flow_editor/flow.json")
    def flow_graph() -> JSONResponse:
        """Genera el grafo de ConversationStep del store en vivo."""
        from frontends.flow_editor.export_flow import export

        return JSONResponse(export(str(cfg.flow_kb_root)))

    @app.get("/taxonomy_explorer")
    @app.get("/taxonomy_explorer/")
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
            "step": ("step", "conversation"),
            "fallback": ("fallback", "conversation"),
            "strategy": ("strategy", "conversation"),
            "trait": ("trait", "user"),
        }

        reader = _orch().reader
        families: dict[str, dict] = {f: {"name": f, "children": {}, "orphans": []}
                                     for f in ("self", "domain", "conversation", "user")}

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

    @app.get("/profiling_viewer")
    @app.get("/profiling_viewer/")
    def profiling_viewer() -> FileResponse:
        return FileResponse(str(PROFILING_DIR / "index.html"))

    @app.get("/api/profiles")
    def profiles() -> JSONResponse:
        """Perfilado: cruza UserTraits (SQL) con TraitAtom (SLDB)."""
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
                    users_out.append({
                        "user_id": u.id,
                        "external_id": u.external_id,
                        "channel": u.channel,
                        "traits": traits,
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

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "kb_root": str(cfg.kb_root), "model": _orch().model}

    return app
