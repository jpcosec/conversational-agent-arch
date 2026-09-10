"""Driver de auditoria HCP: un Orchestrator por proceso, ordenes desde un archivo (una por linea).

Uso: python chat_driver3.py <in.txt> <out.log> <db.sqlite> <turns.jsonl>

Ordenes:
  <external_id>|<mensaje>            un turno
  #perfil <ext> <trait_id>           crea el usuario y le asigna un trait (source=form)
  #greet <ext>                       abre conversacion e inserta el greeting del config como 'assistant'
  #expire <ext> [segundos]           simula inactividad de la conversacion abierta
  #dump <ext>                        estado persistido (user, conversaciones, traits, recontactos, consentimientos)
  #note <texto>                      linea de marca en el log
  /exit
"""
from __future__ import annotations

import json, sqlite3, sys, threading, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from kb_agent.orchestrator import Orchestrator
from kb_agent.perfilador.traits_store import upsert_user_trait, SOURCE_FORM
from kb_agent.project_config import REPO_ROOT, load_project_config

load_dotenv(REPO_ROOT / ".env")
inp, out, db, jl = sys.argv[1:5]
cfg = load_project_config(mode="serving")
orch = Orchestrator.from_config(cfg, db_url=f"sqlite:///{db}", kb_root=cfg.kb_root)
seen = 0
lock = threading.Lock()


def emit(log, text: str) -> None:
    with lock:
        log.write(text + "\n"); log.flush()


def turn(log, ext: str, msg: str) -> None:
    t0 = time.time()
    try:
        t = orch.handle_turn(external_id=ext, message=msg)
    except Exception as exc:  # noqa: BLE001
        emit(log, f"\n=== TURNO {ext} | Tu > {msg}\nERROR {exc!r}"); return
    d = t.get("decisions", {}); step = d.get("step", {}); orq = d.get("orquestador", {}); gate = d.get("gate", {}); rt = d.get("ruteador", {}); ctx = t.get("context", {})
    reply = t.get("reply_text") or ""
    draft = (d.get("conversador") or {}).get("draft")
    trace = {
        "kind": t.get("kind"), "chars": len(reply),
        "step": f"{step.get('before')} -> {step.get('after')}", "missing_slots": step.get("missing_slots"),
        "orq": {"kind": orq.get("kind"), "flow_target": (orq.get("decision") or {}).get("flow_target"), "reason": (orq.get("reason") or "")[:240]},
        "ruteador": {"source": rt.get("source"), "is_empty": rt.get("is_empty"), "bundle": [b.get("doc_id") for b in (rt.get("bundle") or [])]},
        "tools_visibles": [x.get("name") for x in (ctx.get("tools") or []) if isinstance(x, dict)],
        "gate": {"approved": gate.get("approved"), "action": gate.get("action"), "reasons": gate.get("reasons"), "criterios": gate.get("criterion_ids"), "fail_open": gate.get("fail_open"), "skipped": gate.get("skipped")},
        "tool": d.get("tool"), "traits_in_ctx": t.get("used_traits_in_context"), "traits_after": t.get("traits_after"),
        "secs": round(time.time() - t0, 1),
    }
    block = f"\n=== TURNO {ext} | Tu > {msg}\nBot > {reply}"
    if draft and draft != reply:
        block += f"\nDraft > {draft}"
    emit(log, block + "\n" + json.dumps(trace, ensure_ascii=False))
    with lock, open(jl, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ext": ext, "msg": msg, "turn": t}, ensure_ascii=False, default=str) + "\n")


def perfil(log, ext: str, trait_id: str) -> None:
    s = orch.SessionLocal()
    try:
        u = orch.ensure_user(s, ext)
        upsert_user_trait(s, user_id=u.id, trait_id=trait_id, confidence=1.0, source=SOURCE_FORM)
        s.commit()
        emit(log, f"\n### perfil {ext}: user {u.id} <- {trait_id}")
    finally:
        s.close()


def greet(log, ext: str) -> None:
    s = orch.SessionLocal()
    try:
        u = orch.ensure_user(s, ext)
        conv, _ = orch._resolve_conversation(s, user_id=u.id, channel=u.channel)
        orch._persist_chat_history(s, user_id=u.id, role="assistant", content=cfg.greeting, conversation_id=conv.id)
        s.commit()
        emit(log, f"\n### greet {ext}: conv {conv.id}\nBot > {cfg.greeting}")
    finally:
        s.close()


def expire(log, ext: str, secs: int) -> None:
    c = sqlite3.connect(db)
    uid = c.execute("select id from users where external_id=?", (ext,)).fetchone()
    if not uid:
        emit(log, f"\n### expire {ext}: usuario no existe"); return
    past = (datetime.now(timezone.utc) - timedelta(seconds=secs)).strftime("%Y-%m-%d %H:%M:%S.%f")
    n = c.execute("update conversations set last_activity_at=? where user_id=? and status='OPEN'", (past, uid[0])).rowcount
    c.commit(); c.close()
    emit(log, f"\n### expire {ext}: {n} conversacion(es) retrasada(s) {secs}s")


def dump(log, ext: str) -> None:
    c = sqlite3.connect(db)
    u = c.execute("select id, external_id, channel, phone, enrolled from users where external_id=?", (ext,)).fetchone()
    if not u:
        emit(log, f"\n### dump {ext}: usuario no existe"); return
    uid = u[0]
    q = lambda sql: c.execute(sql, (uid,)).fetchall()
    data = {
        "user": u,
        "conversations": q("select id, status, channel from conversations where user_id=? order by id"),
        "session_state": c.execute("select current_node, flow_node, active_domain from session_state where user_id=?", (uid,)).fetchone(),
        "traits": q("select trait_id, confidence, source from user_traits where user_id=?"),
        "recontactos": q("select id, fecha_recontacto, franja_horaria, campania_id, nota_contexto from recontactos where user_id=?"),
        "consentimientos": q("select id, nuevo_estado, campania_id, motivo_verbatim from consentimientos where user_id=?"),
        "last_history": q("select role, substr(content,1,90) from chat_history where user_id=? order by id desc limit 8")[::-1],
    }
    c.close()
    emit(log, f"\n### dump {ext}\n" + json.dumps(data, ensure_ascii=False, default=str))


with open(out, "a", encoding="utf-8") as log:
    emit(log, "READY")
    while True:
        lines = Path(inp).read_text(encoding="utf-8").splitlines() if Path(inp).exists() else []
        if len(lines) <= seen:
            time.sleep(1); continue
        line = lines[seen].strip(); seen += 1
        if not line:
            continue
        if line == "/exit":
            break
        if line.startswith("#note "):
            emit(log, f"\n##### {line[6:]}"); continue
        if line.startswith("#perfil "):
            _, e, tr = line.split(); perfil(log, e, tr); continue
        if line.startswith("#greet "):
            greet(log, line.split()[1]); continue
        if line.startswith("#expire "):
            parts = line.split(); expire(log, parts[1], int(parts[2]) if len(parts) > 2 else 3600); continue
        if line.startswith("#dump "):
            dump(log, line.split()[1]); continue
        ext, msg = line.split("|", 1)
        turn(log, ext.strip(), msg.strip())
    emit(log, "DONE")
orch.close()
