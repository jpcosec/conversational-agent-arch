"""Backend FastAPI conectado a la arquitectura NUEVA (Orchestrator real).

Reemplaza el viejo main.py que dependia de MesaCompiler. Ahora cada turno
pasa por: SLDBReader -> ContextCompiler (SLDB+KGDB) -> RouterStateMachine ->
Conversador (Gemini real) -> Tool dispatcher (SQL real) -> Perfilador async.

Endpoints:
  POST /api/chat                       -> corre un turno real, devuelve el turno enriquecido
  GET  /api/atom/{id}                  -> devuelve un atom del store SLDB
  GET  /                               -> sirve la UI de chat (index.html)
  GET  /conversation_flow_editor       -> sirve el editor de flujo conversacional
  GET  /api/flow                       -> grafo de ConversationStep del store (JSON en vivo)

Uso:
  uvicorn kb_chat_ui.server:app --reload --port 8000
  # o: python -m kb_chat_ui.server
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import load_project_config

EDITOR_DIR = PROJECT_ROOT / "conversation_flow_editor"
PROFILING_DIR = PROJECT_ROOT / "profiling_viewer"

# Config del proyecto/negocio activo. Fuente unica: project.config.yaml
# (+ overrides por entorno). Cambiar de negocio = editar ese archivo.
CFG = load_project_config()
FLOW_KB_ROOT = str(CFG.flow_kb_root)
PROFILING_DB = str(CFG.profiling_db)
MODEL = CFG.model

# ── configuracion ────────────────────────────────────────────
KB_ROOT = CFG.kb_root
DB_PATH = CFG.chat_db

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="KB Chat UI (arquitectura nueva)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Un solo orquestador vivo, con DB en disco (persiste entre requests).
orchestrator = Orchestrator(kb_root=KB_ROOT, db_url=f"sqlite:///{DB_PATH}")

# Contador de turnos por sesion (para turn_id legible en la UI).
_turn_counters: dict[str, int] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    scenario: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    turn: dict


def _external_id(session_id: str) -> str:
    """Mapea session_id de la UI a un external_id estable del orquestador."""
    return f"ui:{session_id}"


def _to_ui_turn(session_id: str, raw: dict) -> dict:
    """Adapta la salida de handle_turn al contrato que consume la UI nueva.

    La UI nueva inspecciona el 'context' (atoms reales del turno) en vez del
    viejo 'mesa' de MesaCompiler.
    """
    _turn_counters[session_id] = _turn_counters.get(session_id, 0) + 1
    turn_id = f"t{_turn_counters[session_id]}"

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
        # Bloque de contexto atomico (reemplaza 'mesa'):
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message vacio")

    session_id = req.session_id or uuid4().hex[:12]
    raw = orchestrator.handle_turn(
        external_id=_external_id(session_id),
        message=req.message,
        # Doctrina: una KB = un negocio. scenario NO filtra; es etiqueta opcional.
        scenario=req.scenario,
    )
    return ChatResponse(session_id=session_id, turn=_to_ui_turn(session_id, raw))


@app.get("/api/atom/{atom_id}")
def get_atom(atom_id: str) -> dict:
    doc = orchestrator.reader.get_doc(atom_id)
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
    return JSONResponse(CFG.to_public_dict())


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
    from conversation_flow_editor.export_flow import export

    return JSONResponse(export(FLOW_KB_ROOT))


@app.get("/profiling_viewer")
@app.get("/profiling_viewer/")
def profiling_viewer() -> FileResponse:
    return FileResponse(str(PROFILING_DIR / "index.html"))


@app.get("/api/profiles")
def profiles() -> JSONResponse:
    """Perfilado: cruza UserTraits (SQL) con TraitAtom (SLDB).

    Devuelve, por usuario, el JSON del perfil (trait_id/confidence/source) y
    el catalogo de fichas TraitAtom a las que apuntan esos trait_id.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from kb_agent.models_sql.identity import Users, UserTraits

    engine = create_engine(f"sqlite:///{PROFILING_DB}", future=True)
    Session = sessionmaker(bind=engine, future=True)

    users_out: list[dict] = []
    trait_ids: set[str] = set()
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

    # Fichas TraitAtom del store (catalogo referenciado por trait_id).
    reader = orchestrator.reader
    fichas: dict[str, dict] = {}
    for doc in reader.find("type.knowledge.trait"):
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
    # Marca trait_ids referenciados desde SQL que no tienen ficha en SLDB.
    missing = sorted(trait_ids - set(fichas.keys()))

    return JSONResponse({
        "users": users_out,
        "fichas": fichas,
        "missing_fichas": missing,
    })


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "kb_root": str(KB_ROOT), "model": MODEL}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
