"""App factory FastAPI del runtime (chat UI + editor de flujo + perfilado + Twilio).

Cada turno pasa por: KnowledgeOperations -> ContextCompiler (SLDB+KGDB) -> RouterStateMachine
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
  GET  /, /flow, /mindmap, /users, /dashboard -> UIs estaticas

La app NO instancia nada al importar el modulo: ``create_app`` recibe (o
construye desde ``project.config.yaml``) el orquestador y lo deja en
``app.state``. Asi los tests levantan la app con DB temporal y LLM inyectado.
"""
from __future__ import annotations

import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from kb_agent.models_sql.identity import Users, UserTraits
from kb_agent.models_sql.leads import Leads, Visitas
from kb_agent.models_sql.session import ChatHistory, SessionState
from kb_agent.models_sql.turns import Turns
from kb_agent.inbound import InboundService, twilio_rest_sender

from kb_agent.orchestrator import Orchestrator, canonical_phone
from kb_agent.project_config import ProjectConfig, load_project_config
from frontends.chat.demo_data import (
    DemoStateMachineConversador,
    demo_atom,
    demo_config,
    demo_events,
    demo_flow,
    demo_health,
    demo_history,
    demo_profiles_payload,
    demo_taxonomy,
    demo_tools,
    demo_viz_graph,
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDITOR_DIR = PROJECT_ROOT / "frontends" / "flow_editor"
CHAT_DIR = PROJECT_ROOT / "frontends" / "chat"
PROFILING_DIR = PROJECT_ROOT / "frontends" / "profiling"
TAXONOMY_DIR = PROJECT_ROOT / "frontends" / "taxonomy"
DEV_DIR = PROJECT_ROOT / "frontends" / "dev"
VIZ_DIR = PROJECT_ROOT / "frontends" / "viz"
DASHBOARD_DIR = PROJECT_ROOT / "frontends" / "dashboard"
LEADS_DIR = PROJECT_ROOT / "frontends" / "leads"
SHARED_DIR = PROJECT_ROOT / "frontends" / "shared"

UI_CHANNEL = "ui"
#: Canal del chat de producto cuando la persona declara su telefono. Un
#: prefijo propio (no "ui") para que ``identity_key: phone`` lo unifique con
#: whatsapp/sms y para poder distinguirlo en las metricas.
WEB_CHANNEL = "web"

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    scenario: str | None = None
    #: Telefono declarado por quien escribe (chat de producto). Con
    #: ``identity_key: phone`` unifica a la MISMA persona que ya escribio por
    #: WhatsApp o SMS. Se canonicaliza en el servidor: el cliente elige su
    #: telefono, nunca un external_id arbitrario de otro usuario.
    phone: str | None = None
    #: Nombre declarado, opcional. Entra a la ficha del lead, no al prompt.
    nombre: str | None = None


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
        "collected": raw.get("collected_slots", {}) or {},
        "system_turn": raw.get("system_turn"),
        # Rastro por agente (ruteador/orquestador/conversador/gate) que arma
        # Orchestrator.handle_turn -- lo consume el panel "Razonamiento" del
        # Turn Inspector (frontends/chat/index.html, renderInspector) para
        # mostrar como piensa el pipeline real, no una lista inventada.
        "decisions": raw.get("decisions", {}),
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


def ordered_flow_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    """Steps del diagrama en orden de recorrido: raices (sin transicion entrante)
    primero, luego BFS por las aristas ``flows_to``; lo inalcanzable al final.

    Es lo que dibuja el stepper del chat: el orden de negocio (saludo ->
    calificacion -> agendar -> datos -> cierre), no el alfabetico.
    """
    nodes = list(flow.get("nodes") or [])
    edges = list(flow.get("edges") or [])
    by_id = {n["id"]: n for n in nodes}
    out_edges: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    incoming: set[str] = set()
    for e in edges:
        src, dst = e.get("source"), e.get("target")
        if src in out_edges and dst in by_id:
            out_edges[src].append(dst)
            incoming.add(dst)
    order: list[str] = []
    queue = [n["id"] for n in nodes if n["id"] not in incoming]
    while queue:
        cur = queue.pop(0)
        if cur in order:
            continue
        order.append(cur)
        queue.extend(t for t in out_edges.get(cur, []) if t not in order)
    order.extend(n["id"] for n in nodes if n["id"] not in order)
    return [
        {"id": sid, "tag": by_id[sid].get("step_tag"), "title": by_id[sid].get("title") or sid, "kind": by_id[sid].get("kind")}
        for sid in order
    ]


#: Estados de NEGOCIO de un lead, en orden de avance. No son los steps del
#: diagrama (eso es el runtime): son lo que el equipo comercial necesita
#: distinguir para saber a quien llamar. Ver ``lead_state``.
LEAD_STATES = ("nuevo", "calificado", "con_preferencia", "datos_completos")

LEAD_STATE_LABELS = {
    "nuevo": "Nuevo",
    "calificado": "Calificado",
    "con_preferencia": "Con preferencia de visita",
    "datos_completos": "Datos completos",
}


def lead_row_payload(lead: Leads | None) -> dict[str, Any]:
    """Fila ``leads`` (tool ``registrar_lead``/``crear_visita``) para la bandeja comercial."""
    if lead is None:
        return {}
    out = {f: getattr(lead, f) for f in Leads.EDITABLE_FIELDS if getattr(lead, f)}
    out["updated_at"] = lead.updated_at.isoformat() if lead.updated_at else None
    return out


def visitas_payload(visitas: Sequence[Visitas]) -> list[dict[str, Any]]:
    """Visitas solicitadas por la tool ``crear_visita`` (el equipo confirma la hora)."""
    return [
        {
            "id": v.id,
            "modalidad": v.modalidad,
            "preferencia": v.preferencia,
            "titulo": v.titulo,
            "duracion_min": v.duracion_min,
            "estado": v.estado,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in visitas
    ]


def merge_lead_into_collected(collected: Mapping[str, Any], lead: Leads | None) -> dict[str, Any]:
    """Lo capturado del mensaje crudo + lo que la tool persistio en ``leads``.

    La fila ``leads`` es la fuente mas confiable (la escribio una tool con
    argumentos ya validados), pero ``collected`` puede traer datos que
    todavia no pasaron por una tool: se unen, con la fila ganando.
    """
    out = dict(collected)
    if lead is not None:
        for slot, field in (("email", "email"), ("telefono", "telefono")):
            if getattr(lead, field):
                out[slot] = getattr(lead, field)
    return out


def lead_state(collected: Mapping[str, Any] | None, traits: Sequence[Any] = ()) -> str:
    """Estado comercial de un lead a partir de lo que ya entrego.

    - ``datos_completos``  -- pidio visita y dejo email Y telefono: el equipo
      puede confirmarle la hora hoy mismo.
    - ``con_preferencia``  -- dijo cuando o como quiere la reunion, pero falta
      algun dato de contacto.
    - ``calificado``       -- el perfilador ya le reconocio traits (para quien
      busca, pais, proyecto), aun sin hablar de visita.
    - ``nuevo``            -- escribio pero todavia no hay nada accionable.
    """
    c = dict(collected or {})
    quiere_visita = bool(c.get("preferencia_visita") or c.get("modalidad"))
    if quiere_visita and c.get("email") and c.get("telefono"):
        return "datos_completos"
    if quiere_visita:
        return "con_preferencia"
    if traits:
        return "calificado"
    return "nuevo"


def _group_conversations(history_rows: list[ChatHistory]) -> list[dict]:
    """Agrupa ChatHistory por CONVERSACION real, no por mensaje.

    Una conversacion (sesion) es una secuencia de turnos que comparten
    ``session_id`` (columna agregada en la migracion ``8df38d93ccd7``). Antes
    esta funcion no existia: cada FILA de ChatHistory (un mensaje, no un
    turno) se listaba como si fuera una conversacion propia con ``n_turns``
    hardcodeado a 1 -- una charla de 6 mensajes aparecia como 6
    "conversaciones", la mitad vacias (las del asistente, sin summary).

    Cada turno real persiste exactamente 1 fila 'user' + 1 fila 'assistant'
    (ver ``Orchestrator.handle_turn`` / ``_persist_chat_history``), asi que
    contar filas con ``role == 'user'`` de una sesion SI es contar turnos
    reales, no mensajes.

    Filas legadas con ``session_id`` NULL: hoy el orquestador en produccion
    no setea ``chat_history.session_id`` (gap fuera del alcance de esta UI,
    ver ``Orchestrator._persist_chat_history``), asi que estas filas no
    tienen forma honesta de saber a que conversacion pertenecen. NO se
    inventa un session_id por fila (eso era el bug anterior): se agrupan por
    DIA de creacion, con ``session_id`` explicitamente ``None`` para que la
    UI no las trate como una conversacion navegable (no hay ``turns`` en la
    tabla `turns` para ese grupo tampoco).
    """
    groups: "OrderedDict[str, list[ChatHistory]]" = OrderedDict()
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    for h in sorted(history_rows, key=lambda r: r.created_at or epoch):
        if h.session_id:
            key = f"sid:{h.session_id}"
        else:
            day = h.created_at.date().isoformat() if h.created_at else "sin-fecha"
            key = f"legacy:{day}"
        groups.setdefault(key, []).append(h)

    conversations: list[dict] = []
    for key, rows in groups.items():
        is_legacy = key.startswith("legacy:")
        n_turns = sum(1 for r in rows if r.role == "user")
        first_user = next((r.content for r in rows if r.role == "user"), "")
        conversations.append({
            "session_id": None if is_legacy else rows[0].session_id,
            "legacy_group": key.split(":", 1)[1] if is_legacy else None,
            "created_at": rows[0].created_at.isoformat() if rows[0].created_at else None,
            "last_active": rows[-1].created_at.isoformat() if rows[-1].created_at else None,
            "summary": (first_user[:80] if first_user else ""),
            "n_turns": n_turns,
            "n_messages": len(rows),
            "result": "unknown",
        })
    conversations.sort(key=lambda c: c["last_active"] or "", reverse=True)
    return conversations


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
    # Demo = opt-in explicito (DEMO_MODE=1, ver ProjectConfig.demo_mode): sin
    # orquestador ni LLM. Nunca por defecto: produccion no setea la variable.
    demo_mode = cfg.demo_mode
    if orchestrator is None and not demo_mode:
        cfg.chat_db.parent.mkdir(parents=True, exist_ok=True)
        orchestrator = Orchestrator.from_config(cfg)

    app = FastAPI(title=(demo_config()["runtime_title"] if demo_mode else cfg.runtime_title))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.cfg = cfg
    app.state.orchestrator = orchestrator
    app.state.demo_mode = demo_mode
    app.state.demo_sessions = {}
    app.state.demo_llm = DemoStateMachineConversador() if demo_mode else None
    app.demo_mode = demo_mode
    app.mount("/static", StaticFiles(directory=str(SHARED_DIR)), name="static")

    def _orch() -> Orchestrator:
        if app.state.orchestrator is None:
            raise HTTPException(status_code=503, detail="orchestrator unavailable in demo mode")
        return app.state.orchestrator

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        if not req.message or not req.message.strip():
            raise HTTPException(status_code=400, detail="message vacio")

        session_id = req.session_id or uuid4().hex[:12]

        if app.state.demo_mode:
            sessions: dict[str, dict[str, Any]] = app.state.demo_sessions
            session = sessions.setdefault(session_id, {"session_id": session_id, "flow_node": "bienvenida", "slots": {}, "traits": [], "history": []})
            raw = app.state.demo_llm.handle_turn(session, req.message)
            raw["allowed_transitions"] = next((n["allowed_transitions"] for n in demo_flow()["nodes"] if n["id"] == raw.get("flow_node")), [])
            # demo no pasa por el orquestador (no persiste turns): genera su
            # propio id unico por turno, sin contador compartido.
            return ChatResponse(session_id=session_id, turn=to_ui_turn(uuid4().hex[:12], raw))

        # Identidad: con telefono declarado el usuario es el MISMO que escribe
        # por WhatsApp (identity_key=phone resuelve `web:+569...`); sin el,
        # la sesion del navegador (`ui:<session_id>`), anonima.
        phone = canonical_phone(req.phone or "") if req.phone else None
        external_id = f"{WEB_CHANNEL}:{phone}" if phone else _external_id(session_id)
        contact: dict[str, str] = {}
        if phone:
            contact["telefono"] = phone
        if req.nombre and req.nombre.strip():
            contact["nombre"] = req.nombre.strip()

        raw = _orch().handle_turn(
            external_id=external_id,
            message=req.message,
            scenario=req.scenario,
            channel=WEB_CHANNEL if phone else UI_CHANNEL,
            contact=contact or None,
        )
        # El orquestador genera y persiste el turn_id; la UI usa EXACTAMENTE
        # ese, asi el id en vivo coincide con el que devuelve /api/history y no
        # colisiona entre requests concurrentes (ya no hay contador compartido).
        return ChatResponse(session_id=session_id, turn=to_ui_turn(raw["turn_id"], raw))

    def _twilio_reply_mode() -> str:
        """``async`` (default si hay TWILIO_ACCOUNT_SID para mandar por REST) o
        ``sync`` (TwiML en linea). Override explicito: TWILIO_REPLY_MODE."""
        mode = (os.environ.get("TWILIO_REPLY_MODE") or "").strip().lower()
        if mode in {"sync", "async"}:
            return mode
        return "async" if os.environ.get("TWILIO_ACCOUNT_SID") else "sync"

    @app.post("/webhooks/twilio")
    async def twilio_inbound(request: Request, background: BackgroundTasks) -> Response:
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not token:
            raise HTTPException(status_code=503, detail="twilio not configured (TWILIO_AUTH_TOKEN)")
        form = {key: value for key, value in (await request.form()).items()}
        signature = request.headers.get("X-Twilio-Signature", "")
        if not RequestValidator(token).validate(str(request.url), form, signature):
            raise HTTPException(status_code=403, detail="invalid twilio signature")

        # InboundService: normaliza el remitente (SMS pelado -> sms:+56...),
        # persiste el mensaje como InboundMessage (source del turno, con el
        # MessageSid del proveedor), resuelve el usuario y corre el turno. Un
        # reintento de Twilio con el mismo MessageSid no corre un segundo
        # turno: devuelve la respuesta guardada, o <Response/> vacio si el
        # original sigue corriendo.
        twiml = MessagingResponse()
        if _twilio_reply_mode() == "async":
            # Twilio corta el webhook a los 15 s y un turno con LLM tarda mas:
            # se responde vacio al instante y la respuesta sale por REST
            # cuando el turno termina (InboundService.run_turn_and_send).
            sender = getattr(app.state, "twilio_sender", None) or twilio_rest_sender(
                os.environ["TWILIO_ACCOUNT_SID"], token
            )
            svc = InboundService(_orch(), sender=sender)
            row = await run_in_threadpool(svc.record, form)
            if row is not None:
                background.add_task(svc.run_turn_and_send, row)
            return Response(str(twiml), media_type="application/xml")

        result = await run_in_threadpool(InboundService(_orch()).receive, form)
        if result.reply_text:
            twiml.message(result.reply_text)
        return Response(str(twiml), media_type="application/xml")

    @app.get("/api/atom/{atom_id}")
    def get_atom(atom_id: str) -> dict:
        if app.state.demo_mode:
            doc = demo_atom(atom_id)
            if doc is None:
                raise HTTPException(status_code=404, detail=f"atom {atom_id} no encontrado")
            return {
                "atom_id": doc.get("atom_id", atom_id),
                "title": doc.get("title") or atom_id,
                "body": doc.get("body", ""),
                "tags": doc.get("tags", []),
                "five_wh_one_plus": doc.get("five_wh_one_plus"),
                "path": doc.get("path"),
            }
        doc = _orch().knowledge_ops.doc(atom_id)
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
        """Config publica del negocio de la rama (marca, greeting, modelo) para las UIs."""
        return JSONResponse(demo_config() if app.state.demo_mode else cfg.to_public_dict())

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(BASE_DIR / "index.html"))

    @app.get("/flow")
    @app.get("/flow/")
    def flow_editor() -> FileResponse:
        return FileResponse(str(EDITOR_DIR / "index.html"))

    @app.get("/api/flow")
    def flow_graph() -> JSONResponse:
        if app.state.demo_mode:
            return JSONResponse(demo_flow())
        from frontends.flow_editor.export_flow import export

        return JSONResponse(export(str(cfg.flow_kb_root)))

    @app.get("/mindmap")
    @app.get("/mindmap/")
    def taxonomy_explorer() -> FileResponse:
        return FileResponse(str(TAXONOMY_DIR / "index.html"))

    @app.get("/dashboard")
    @app.get("/dashboard/")
    def dashboard() -> FileResponse:
        return FileResponse(str(DASHBOARD_DIR / "index.html"))

    @app.get("/api/taxonomy")
    def taxonomy() -> JSONResponse:
        if app.state.demo_mode:
            return JSONResponse(demo_taxonomy())
        """Arbol taxonomico completo: familias -> subpaths -> atoms.

        Cada doc tiene un tag type.knowledge.{model_name}.
        Los tags con prefijo de su familia definen la jerarquia.
        """
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

        knowledge = _orch().knowledge_ops
        families: dict[str, dict] = {f: {"name": f, "children": {}, "orphans": []}
                                     for f in ("self", "domain", "conversation", "gate", "user")}

        for doc in knowledge.docs_by_tag("type.knowledge"):
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
                for seg in segments[:-1]:
                    if seg not in node:
                        node[seg] = {"children": {}, "atoms": []}
                    node = node[seg]["children"]
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
        if app.state.demo_mode:
            return JSONResponse(demo_tools())
        knowledge = _orch().knowledge_ops
        tools_list: list[dict] = []
        for doc in knowledge.docs_by_type("tool"):
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

    @app.get("/chat")
    @app.get("/chat/")
    def product_chat() -> FileResponse:
        return FileResponse(str(CHAT_DIR / "product.html"))

    @app.get("/leads")
    @app.get("/leads/")
    def leads_view() -> FileResponse:
        return FileResponse(str(LEADS_DIR / "index.html"))

    @app.get("/users")
    @app.get("/users/")
    def profiling_viewer() -> FileResponse:
        return FileResponse(str(PROFILING_DIR / "index.html"))

    @app.get("/api/viz/graph")
    def viz_graph(edge_threshold: float | None = None, max_edges_per_node: int | None = None) -> JSONResponse:
        if app.state.demo_mode:
            return JSONResponse(demo_viz_graph())
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
            graph = build_graph(_orch().knowledge_ops, edge_threshold=threshold, max_edges_per_node=max_edges)
            cache[key] = graph
            app.state.viz_cache = cache

        return JSONResponse({"kb": cfg.name, **graph})

    @app.get("/api/profiles")
    def profiles() -> JSONResponse:
        if app.state.demo_mode:
            return JSONResponse(demo_profiles_payload())
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

                    # conversaciones del usuario: agrupadas por sesion real,
                    # no una entrada por fila/mensaje (ver _group_conversations).
                    history_rows = s.query(ChatHistory).filter(
                        ChatHistory.user_id == u.id
                    ).order_by(ChatHistory.created_at.asc()).all()
                    all_conversations = _group_conversations(history_rows)
                    conversations = all_conversations[:20]
                    total_turns = sum(c["n_turns"] for c in all_conversations)
                    last_active = all_conversations[0]["last_active"] if all_conversations else None

                    users_out.append({
                        "user_id": u.id,
                        "external_id": u.external_id,
                        "channel": u.channel,
                        "traits": traits,
                        "traits_count": len(traits),
                        "total_turns": total_turns,
                        "last_active": last_active,
                        "created_at": u.created_at.isoformat() if hasattr(u, "created_at") and u.created_at else None,
                        "conversations": conversations,
                    })
        finally:
            engine.dispose()

        fichas: dict[str, dict] = {}
        for doc in _orch().knowledge_ops.docs_by_type("trait"):
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
        if app.state.demo_mode:
            return JSONResponse(demo_events(user_id))
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

    @app.get("/api/metrics")
    def metrics(days: int = 14) -> JSONResponse:
        """Metricas reales del runtime, leidas del sqlite.

        Reemplaza el mock estatico del dashboard. Todo sale de ``turns``
        (rastro por turno) y ``users``/``session_state``; nada es sintetico.
        ``fallback`` y ``derivados`` son los dos indicadores que de verdad
        dicen si el agente esta respondiendo: un fallback es "no supe" y un
        derivado es un borrador que el policy gate no dejo salir.
        """
        if app.state.demo_mode:
            return JSONResponse({"turnos": 0, "por_dia": [], "kinds": {}, "fallback_pct": 0.0,
                                 "derivados_pct": 0.0, "leads": {}, "latencia_ms": {}, "days": days})
        orch = _orch()
        rows: list[tuple] = []
        with orch.SessionLocal() as s:
            # Se seleccionan COLUMNAS, no la entidad: no hace falta cargar
            # ``kind`` (enum) para contar turnos, y asi la vista no depende de
            # que cada fila historica tenga el enum en la forma que espera el
            # modelo (ver migracion e5f6a7b8c9d1).
            for created, decision, gate, duration in s.query(
                Turns.created_at, Turns.decision, Turns.gate, Turns.duration_ms
            ).order_by(Turns.created_at.asc()).all():
                kind = decision.get("kind") if isinstance(decision, dict) else None
                approved = gate.get("approved") if isinstance(gate, dict) else None
                rows.append((created, kind, approved, duration))
            total_users = s.query(Users).count()
        leads_payload = leads().body
        import json as _json

        leads_data = _json.loads(leads_payload)

        total = len(rows)
        kinds: dict[str, int] = {}
        for _, kind, _a, _d in rows:
            kinds[kind or "desconocido"] = kinds.get(kind or "desconocido", 0) + 1
        por_dia: dict[str, int] = {}
        for created, _k, _a, _d in rows:
            if created is not None:
                por_dia[created.date().isoformat()] = por_dia.get(created.date().isoformat(), 0) + 1
        derivados = sum(1 for _c, _k, approved, _d in rows if approved is False)
        fallbacks = kinds.get("fallback", 0)
        durations = sorted(d for _c, _k, _a, d in rows if isinstance(d, int))
        pct = lambda n: round(100.0 * n / total, 1) if total else 0.0
        return JSONResponse({
            "days": days,
            "turnos": total,
            "usuarios": total_users,
            "kinds": kinds,
            "por_dia": [{"dia": d, "turnos": n} for d, n in sorted(por_dia.items())][-days:],
            "fallback_pct": pct(fallbacks),
            "fallback_n": fallbacks,
            "derivados_pct": pct(derivados),
            "derivados_n": derivados,
            "leads": leads_data.get("counts", {}),
            "leads_total": len(leads_data.get("leads", [])),
            "visitas_por_confirmar": len(leads_data.get("queue", [])),
            "latencia_ms": {
                "n": len(durations),
                "mediana": durations[len(durations) // 2] if durations else None,
                "p90": durations[int(len(durations) * 0.9)] if durations else None,
                "max": durations[-1] if durations else None,
            },
        })

    @app.get("/api/leads")
    def leads() -> JSONResponse:
        """Bandeja comercial: un lead por usuario, con su estado de negocio,
        lo que ya entrego y la cola de visitas por confirmar.

        Existe porque la tool de agenda (flujo n8n) todavia no llego: el
        equipo confirma las horas a mano y hasta ahora no tenia donde ver
        quien pidio visita ni con que datos (ver source/DUDAS-KB.md, P5).
        """
        if app.state.demo_mode:
            return JSONResponse({"leads": [], "queue": [], "counts": {k: 0 for k in LEAD_STATES}})
        orch = _orch()
        out: list[dict] = []
        with orch.SessionLocal() as s:
            for u in s.query(Users).order_by(Users.id).all():
                state_row = s.get(SessionState, u.id)
                slots = state_row.flow_slots if state_row is not None and isinstance(state_row.flow_slots, dict) else {}
                lead_row = s.query(Leads).filter(Leads.user_id == u.id).one_or_none()
                visitas = s.query(Visitas).filter(Visitas.user_id == u.id).order_by(Visitas.id.desc()).all()
                collected = merge_lead_into_collected(dict(slots.get("collected") or {}), lead_row)
                trait_ids = [
                    r[0] for r in s.query(UserTraits.trait_id).filter(UserTraits.user_id == u.id)
                    .order_by(UserTraits.trait_id).all()
                ]
                traits = []
                for tid in trait_ids:
                    doc = orch.knowledge_ops.doc(tid) or {}
                    traits.append({"trait_id": tid, "title": doc.get("title") or tid})
                history_rows = s.query(ChatHistory).filter(
                    ChatHistory.user_id == u.id
                ).order_by(ChatHistory.created_at.asc()).all()
                conversations = _group_conversations(history_rows)
                estado = lead_state(collected, traits)
                out.append({
                    "user_id": u.id,
                    "external_id": u.external_id,
                    "channel": u.channel,
                    "estado": estado,
                    "estado_label": LEAD_STATE_LABELS[estado],
                    "paso": state_row.flow_node if state_row is not None else None,
                    "traits": traits,
                    "collected": collected,
                    "lead": lead_row_payload(lead_row),
                    "visitas": visitas_payload(visitas),
                    "visita_solicitada": any(v.estado == "solicitada" for v in visitas),
                    "falta": [k for k in ("preferencia_visita", "modalidad", "email", "telefono") if not collected.get(k)],
                    "n_turnos": sum(c["n_turns"] for c in conversations),
                    "last_active": conversations[0]["last_active"] if conversations else None,
                    "primer_mensaje": conversations[-1]["summary"] if conversations else "",
                })
        out.sort(key=lambda l: (l["last_active"] or ""), reverse=True)
        counts = {k: sum(1 for l in out if l["estado"] == k) for k in LEAD_STATES}
        # Cola: pidio visita (dijo cuando o como). Los que ya tienen todos los
        # datos van primero -- se pueden confirmar sin volver a escribirles.
        queue = [l for l in out if l["estado"] in ("con_preferencia", "datos_completos") or l["visita_solicitada"]]
        queue.sort(key=lambda l: (not l["visita_solicitada"], l["estado"] != "datos_completos", l["last_active"] or ""))
        return JSONResponse({"leads": out, "queue": queue, "counts": counts})

    @app.get("/api/lead")
    def lead(session_id: str | None = None, external_id: str | None = None) -> JSONResponse:
        """Ficha del lead de UNA conversacion: paso activo dentro del flujo,
        perfil (traits resueltos contra su TraitAtom) y datos capturados del
        mensaje crudo (``session_state.flow_slots.collected``, ver
        ``kb_agent/lead_slots.py``). Es lo que el equipo comercial necesita
        para confirmar una visita sin leer el rastro tecnico del turno.
        """
        if not session_id and not external_id:
            raise HTTPException(status_code=400, detail="se requiere session_id o external_id")
        ext = external_id or _external_id(session_id or "")
        if app.state.demo_mode:
            return JSONResponse({"external_id": ext, "step": None, "steps": [], "traits": [], "collected": {}})
        from frontends.flow_editor.export_flow import export

        steps = ordered_flow_steps(export(str(cfg.flow_kb_root)))
        orch = _orch()
        active: str | None = None
        collected: dict[str, Any] = {}
        trait_ids: list[str] = []
        lead_payload: dict[str, Any] = {}
        visitas_list: list[dict[str, Any]] = []
        with orch.SessionLocal() as s:
            user = s.query(Users).filter(Users.external_id == ext).first()
            if user is not None:
                state = s.get(SessionState, user.id)
                lead_row = s.query(Leads).filter(Leads.user_id == user.id).one_or_none()
                lead_payload = lead_row_payload(lead_row)
                visitas_list = visitas_payload(
                    s.query(Visitas).filter(Visitas.user_id == user.id).order_by(Visitas.id.desc()).all()
                )
                if state is not None:
                    active = state.flow_node
                    slots = state.flow_slots if isinstance(state.flow_slots, dict) else {}
                    collected = merge_lead_into_collected(dict(slots.get("collected") or {}), lead_row)
                trait_ids = [
                    r[0] for r in s.query(UserTraits.trait_id).filter(UserTraits.user_id == user.id)
                    .order_by(UserTraits.trait_id).all()
                ]
        active_idx = next((i for i, st in enumerate(steps) if st["tag"] == active), None)
        for i, st in enumerate(steps):
            st["state"] = "pending" if active_idx is None else ("done" if i < active_idx else "active" if i == active_idx else "pending")
        traits = []
        for tid in trait_ids:
            doc = orch.knowledge_ops.doc(tid) or {}
            traits.append({"trait_id": tid, "title": doc.get("title") or tid, "category": doc.get("category") or ""})
        return JSONResponse({
            "external_id": ext,
            "step": next((st for st in steps if st["state"] == "active"), None),
            "steps": steps,
            "traits": traits,
            "collected": collected,
            "lead": lead_payload,
            "visitas": visitas_list,
        })

    @app.get("/api/history")
    def history(external_id: str | None = None, session_id: str | None = None) -> JSONResponse:
        """Historial de una conversacion, con su rastro por turno (tabla ``turns``).

        Acepta ``session_id`` (UNA conversacion real, preferido: linkeado desde
        ``/users`` -> ``/?session=<session_id>``) o ``external_id`` (todas las
        filas de ChatHistory de ese usuario, comportamiento legado -- sigue
        existiendo para las filas sin ``session_id``, ver ``_group_conversations``).

        Con ``session_id`` ademas devuelve ``turns``: el rastro persistido por
        ``Orchestrator._persist_turn`` (bundle, decision, gate, draft, tool) para
        que el Turn Inspector funcione al reabrir una conversacion pasada, no
        solo en vivo (antes de esto no habia rastro guardado y el panel
        quedaba vacio).

        Nota sobre ``Turns.session_id``: ``Orchestrator._persist_turn`` lo
        llena con el ``external_id`` del turno, NO con
        ``chat_history.session_id`` (que hoy el orquestador no setea en
        produccion, ver ``_group_conversations``). Para el canal ``ui`` esto
        igual funciona: ``external_id`` ya es ``f"ui:{session_id}"``, estable
        por conversacion de navegador. Por eso el rastro se busca por
        ``session_id`` (conversaciones sembradas/futuras con la columna
        seteada) Y por ``external_id`` (conversaciones en vivo de hoy).
        """
        if app.state.demo_mode:
            return JSONResponse(demo_history(external_id or ""))
        if not external_id and not session_id:
            raise HTTPException(status_code=400, detail="se requiere external_id o session_id")
        engine = create_engine(f"sqlite:///{cfg.profiling_db}", future=True)
        Session = sessionmaker(bind=engine, future=True)
        msgs: list[dict] = []
        turns_out: list[dict] = []
        try:
            with Session() as s:
                if session_id:
                    rows = s.query(ChatHistory).filter(
                        ChatHistory.session_id == session_id
                    ).order_by(ChatHistory.created_at.asc()).all()
                else:
                    user = s.query(Users).filter(Users.external_id == external_id).first()
                    rows = (
                        s.query(ChatHistory).filter(ChatHistory.user_id == user.id)
                        .order_by(ChatHistory.created_at.asc()).all()
                        if user else []
                    )
                for h in rows:
                    msgs.append({
                        "role": h.role,
                        "content": h.content,
                        "created_at": h.created_at.isoformat() if h.created_at else None,
                        "session_id": h.session_id,
                    })

                turns_session_key = session_id or external_id
                if turns_session_key:
                    for t in s.query(Turns).filter(
                        Turns.session_id == turns_session_key
                    ).order_by(Turns.created_at.asc()).all():
                        turns_out.append({
                            "turn_id": t.turn_id,
                            "created_at": t.created_at.isoformat() if t.created_at else None,
                            "step_before": t.step_before,
                            "step_after": t.step_after,
                            "decision": t.decision,
                            "draft": t.draft,
                            "gate": t.gate,
                            "bundle": t.bundle,
                            "tool": t.tool,
                        })
        finally:
            engine.dispose()
        return JSONResponse({
            "external_id": external_id,
            "session_id": session_id,
            "messages": msgs,
            "turns": turns_out,
        })

    @app.get("/dev")
    @app.get("/dev/")
    def dev_console() -> FileResponse:
        return FileResponse(str(DEV_DIR / "index.html"), media_type="text/html")

    @app.get("/dev/prompts")
    @app.get("/dev/prompts/")
    def dev_prompts() -> FileResponse:
        return FileResponse(str(DEV_DIR / "prompts.html"), media_type="text/html")

    @app.get("/api/system-prompts")
    def system_prompts() -> JSONResponse:
        if app.state.demo_mode:
            return JSONResponse({
                "agents": {
                    "conversador": {
                        "role": "conversador",
                        "framing": "Eres Antonia, asistente virtual de Teva para profesionales de la salud (HCP).",
                        "static_instruction": "Eres el CONVERSADOR del sistema. Redactas la respuesta final que ve el usuario.",
                    },
                    "router": {
                        "role": "router",
                        "framing": "Operas sobre la KB de campañas HCP de Teva.",
                        "static_instruction": "Eres el RUTEADOR DE CONTEXTO de un agente conversacional...",
                    },
                    "orchestrator": {
                        "role": "orchestrator",
                        "framing": "Eres el ORQUESTADOR de un agente conversacional.",
                        "static_instruction": "",
                    },
                    "gate": {
                        "role": "gate",
                        "framing": "Eres el GATE regulatorio de un programa de soporte a pacientes (farmacovigilancia).",
                        "static_instruction": "",
                    },
                },
                "kb_root": "demo",
            })

        try:
            orch = _orch()
            ops = orch.knowledge_ops
            from kb_agent.agents import render_gate_criteria, render_orchestrator_flow, render_router_instruction
            from kb_agent.models.knowledge import AgentFraming, GateCriterion, ConversationStep

            # Read AgentFraming docs by role parsing raw files directly
            import yaml as _yaml
            framing_docs = {}
            for agent_id in ["agent-hcp-conversador", "agent-hcp-gate", "agent-hcp-orchestrator", "agent-hcp-router"]:
                agent_path = cfg.kb_root / "atoms" / f"{agent_id}.md"
                if agent_path.exists():
                    parts = agent_path.read_text(encoding="utf-8").split("---")
                    if len(parts) >= 2:
                        try:
                            fm = _yaml.safe_load(parts[1])
                            if fm:
                                role = (fm.get("role") or "").strip().lower()
                                if role:
                                    framing_docs[role] = {"framing": fm.get("framing", ""), "examples": fm.get("examples", "")}
                        except Exception:
                            pass

            # Build each agent's system prompt
            agents = {}

            # Router
            router_framing = framing_docs.get("router", {}).get("framing")
            agents["router"] = {
                "role": "router",
                "framing": router_framing or "",
                "static_instruction": render_router_instruction(framing=router_framing or None),
            }

            # Gate
            gate_criteria = list(ops.docs_by_type("gate"))
            gate_framing = framing_docs.get("gate", {}).get("framing")
            agents["gate"] = {
                "role": "gate",
                "framing": gate_framing or "",
                "static_instruction": render_gate_criteria(gate_criteria, framing=gate_framing or None),
                "criteria": [{"id": c.get("id"), "criterion": c.get("criterion")} for c in gate_criteria],
            }

            # Orchestrator
            steps = list(ops.docs_by_type("step"))
            orch_framing = framing_docs.get("orchestrator", {}).get("framing")
            agents["orchestrator"] = {
                "role": "orchestrator",
                "framing": orch_framing or "",
                "static_instruction": render_orchestrator_flow(steps, framing=orch_framing or None),
                "step_count": len(steps),
            }

            # Conversador (framing from KB, body hardcoded in orchestrator)
            conv_framing = framing_docs.get("conversador", {}).get("framing")
            agents["conversador"] = {
                "role": "conversador",
                "framing": conv_framing or "",
                "static_instruction": conv_framing or "Eres el CONVERSADOR del sistema. Redactas la respuesta final que ve el usuario.",
            }

            return JSONResponse({"agents": agents, "kb_root": str(cfg.kb_root)})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/health")
    def health() -> dict:
        if app.state.demo_mode:
            return demo_health()
        return {"status": "ok", "kb_root": str(cfg.kb_root), "model": _orch().model}

    return app
