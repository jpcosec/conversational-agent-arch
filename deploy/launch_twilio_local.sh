#!/usr/bin/env bash
# Levanta el runtime local y lo conecta al numero Twilio via ngrok.
#
# Uso:
#   deploy/launch_twilio_local.sh            # = up
#   deploy/launch_twilio_local.sh up         # migra sqlite, uvicorn, ngrok, apunta el numero al tunel
#   deploy/launch_twilio_local.sh status     # que hay corriendo y a donde apunta el numero
#   deploy/launch_twilio_local.sh down       # mata uvicorn/ngrok y restaura el webhook anterior del numero
#
# Requiere en .env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SMS_FROM
# (mas las de Vertex: GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT).
# Requiere ngrok instalado y con authtoken (ngrok config add-authtoken ...).
#
# Canales: el webhook SMS vive en el numero (IncomingPhoneNumber.sms_url). El de
# WhatsApp vive en el *sender* de WhatsApp (Messaging v2 Channels Senders): si
# whatsapp:+<numero> esta registrado como sender en la cuenta, tambien se apunta
# al tunel; si no, se avisa y queda solo SMS. El endpoint /webhooks/twilio es el
# mismo para ambos (solo mira From y Body).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
LOG_DIR="$REPO_ROOT/runs/logs"
STATE_DIR="$LOG_DIR/twilio_local"
UVICORN_PID="$STATE_DIR/uvicorn.pid"
NGROK_PID="$STATE_DIR/ngrok.pid"
PREV_WEBHOOK="$STATE_DIR/prev_webhooks.json"
NGROK_API="http://127.0.0.1:4040/api/tunnels"
mkdir -p "$LOG_DIR" "$STATE_DIR"

log() { printf '\033[1;34m[twilio-local]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[twilio-local] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

load_env() {
    [ -f .env ] || die "no hay .env en $REPO_ROOT"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    for v in TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_SMS_FROM; do
        [ -n "${!v:-}" ] || die "falta $v en .env"
    done
}

port_in_use() { ss -ltn 2>/dev/null | grep -q ":$PORT "; }

pid_alive() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

# ── sqlite: mismo criterio que deploy/modal_app.py::_migrate_data_volume ──────
# create_all() nunca altera tablas existentes; una base sin alembic_version es
# un hibrido que no se puede migrar de forma confiable (ya paso: users.phone).
# En local no hay datos que cuidar: se respalda y se recrea en head.
migrate_db() {
    local db
    db="$(python -c 'from kb_agent.project_config import load_project_config; print(load_project_config().chat_db)')"
    if [ -f "$db" ] && ! sqlite3 "$db" "select 1 from alembic_version" >/dev/null 2>&1; then
        local bak="$db.bak-$(date +%Y%m%d%H%M%S)"
        log "sqlite sin alembic_version -> respaldo en $bak y recreo"
        mv "$db" "$bak"
    fi
    alembic upgrade head 2>&1 | grep -E "Running upgrade|ERROR" || true
    log "sqlite en $(alembic current 2>/dev/null | tail -1)"
}

# ── uvicorn ───────────────────────────────────────────────────────────────────
start_uvicorn() {
    if port_in_use; then
        log "puerto $PORT ya ocupado; reutilizo el servidor existente"
        return
    fi
    nohup python -m uvicorn frontends.chat.server:app --host "$HOST" --port "$PORT" \
        > "$LOG_DIR/ui.log" 2>&1 &
    echo $! > "$UVICORN_PID"
    for _ in $(seq 1 60); do
        curl -sf "http://$HOST:$PORT/api/config" >/dev/null 2>&1 && break
        sleep 1
    done
    curl -sf "http://$HOST:$PORT/api/config" >/dev/null 2>&1 \
        || die "uvicorn no respondio; ver $LOG_DIR/ui.log"
    log "UI en http://$HOST:$PORT (log: $LOG_DIR/ui.log)"
}

# ── ngrok ─────────────────────────────────────────────────────────────────────
ngrok_url() {
    curl -sf "$NGROK_API" 2>/dev/null | python -c '
import sys, json
for t in json.load(sys.stdin).get("tunnels", []):
    if t.get("public_url", "").startswith("https://"):
        print(t["public_url"]); break
' 2>/dev/null || true
}

start_ngrok() {
    command -v ngrok >/dev/null || die "ngrok no esta instalado"
    local url
    url="$(ngrok_url)"
    if [ -n "$url" ]; then
        log "ngrok ya corriendo: $url"
        echo "$url"
        return
    fi
    nohup ngrok http "$PORT" --log stdout > "$LOG_DIR/ngrok.log" 2>&1 &
    echo $! > "$NGROK_PID"
    for _ in $(seq 1 30); do
        url="$(ngrok_url)"
        [ -n "$url" ] && break
        sleep 1
    done
    [ -n "$url" ] || die "ngrok no expuso URL; ver $LOG_DIR/ngrok.log"
    log "tunel: $url"
    echo "$url"
}

# ── Twilio: apuntar / restaurar los webhooks del numero (SMS + WhatsApp) ─────
twilio_point_number() {
    local webhook="$1"
    python - "$webhook" "$PREV_WEBHOOK" <<'PYEOF'
import json, os, sys
from twilio.rest import Client

webhook, prev_path = sys.argv[1], sys.argv[2]
number = os.environ["TWILIO_SMS_FROM"]
c = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
# Se guarda el estado previo solo la PRIMERA vez: un segundo `up` sin `down`
# no debe pisar el webhook original con la URL de un tunel viejo.
prev = json.load(open(prev_path)) if os.path.exists(prev_path) else None
state = prev or {}

# SMS: webhook del numero.
nums = c.incoming_phone_numbers.list(phone_number=number)
if not nums:
    sys.exit(f"el numero {number} no esta en la cuenta")
n = nums[0]
if prev is None:
    state["sms"] = {"sid": n.sid, "sms_url": n.sms_url, "sms_method": n.sms_method}
n.update(sms_url=webhook, sms_method="POST")
print(f"[twilio-local] SMS      {n.phone_number} sms_url -> {webhook}")

# WhatsApp: el webhook vive en el sender, no en el numero.
wa = [s for s in c.messaging.v2.channels_senders.list(channel="whatsapp")
      if s.sender_id == f"whatsapp:{number}"]
if wa:
    s = wa[0]
    if prev is None:
        state["whatsapp"] = {"sid": s.sid, "webhook": s.webhook}
    c.request(
        "POST", f"https://messaging.twilio.com/v2/Channels/Senders/{s.sid}",
        data=json.dumps({"webhook": {"callback_url": webhook, "callback_method": "POST"}}),
        headers={"Content-Type": "application/json"},
    )
    print(f"[twilio-local] WhatsApp {s.sender_id} ({s.status}) webhook -> {webhook}")
else:
    print(f"[twilio-local] WhatsApp whatsapp:{number} NO esta registrado como sender en esta cuenta "
          "(Console > Messaging > Senders > WhatsApp senders). Queda solo SMS.")

if prev is None:
    json.dump(state, open(prev_path, "w"))
PYEOF
}

twilio_restore_number() {
    [ -f "$PREV_WEBHOOK" ] || { log "sin webhook previo guardado; no toco el numero"; return; }
    python - "$PREV_WEBHOOK" <<'PYEOF'
import json, os, sys
from twilio.rest import Client

prev = json.load(open(sys.argv[1]))
c = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
if "sms" in prev:
    p = prev["sms"]
    n = c.incoming_phone_numbers(p["sid"]).update(sms_url=p["sms_url"], sms_method=p["sms_method"] or "POST")
    print(f"[twilio-local] SMS      {n.phone_number} sms_url restaurado -> {n.sms_url}")
if prev.get("whatsapp", {}).get("webhook"):
    p = prev["whatsapp"]
    c.request(
        "POST", f"https://messaging.twilio.com/v2/Channels/Senders/{p['sid']}",
        data=json.dumps({"webhook": p["webhook"]}),
        headers={"Content-Type": "application/json"},
    )
    print(f"[twilio-local] WhatsApp webhook restaurado -> {p['webhook'].get('callback_url')}")
PYEOF
    rm -f "$PREV_WEBHOOK"
}

twilio_show_number() {
    python - <<'PYEOF'
import os
from twilio.rest import Client

number = os.environ["TWILIO_SMS_FROM"]
c = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
a = c.api.accounts(os.environ["TWILIO_ACCOUNT_SID"]).fetch()
print(f"  cuenta   : {a.friendly_name} ({a.status})")
for n in c.incoming_phone_numbers.list(phone_number=number):
    print(f"  SMS      : {n.phone_number}  sms_url={n.sms_url} [{n.sms_method}]")
wa = [s for s in c.messaging.v2.channels_senders.list(channel="whatsapp")
      if s.sender_id == f"whatsapp:{number}"]
if wa:
    w = wa[0].webhook or {}
    print(f"  WhatsApp : {wa[0].sender_id} ({wa[0].status})  callback_url={w.get('callback_url')}")
else:
    print(f"  WhatsApp : whatsapp:{number} no registrado como sender en esta cuenta")
PYEOF
}

# ── prueba local firmada (sin pasar por Twilio) ───────────────────────────────
smoke_signed_post() {
    python - "$HOST" "$PORT" <<'PYEOF'
import os, sys, requests
from twilio.request_validator import RequestValidator

url = f"http://{sys.argv[1]}:{sys.argv[2]}/webhooks/twilio"
form = {"From": "+56900000000", "To": os.environ["TWILIO_SMS_FROM"], "Body": "hola"}
sig = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"]).compute_signature(url, form)
r = requests.post(url, data=form, headers={"X-Twilio-Signature": sig}, timeout=180)
ok = r.status_code == 200 and "<Response>" in r.text
print(f"[twilio-local] smoke firmado local: {r.status_code} {'OK' if ok else 'FALLO'}")
if not ok:
    print(r.content.decode("utf-8", "replace")[:400])
    sys.exit(1)
PYEOF
}

cmd_up() {
    load_env
    migrate_db
    start_uvicorn
    smoke_signed_post
    local url
    url="$(start_ngrok | tail -1)"
    twilio_point_number "$url/webhooks/twilio"
    cat <<MSG

  Listo. Manda un SMS (o WhatsApp, si el sender existe) a $TWILIO_SMS_FROM.
  Deberias ver "POST /webhooks/twilio 200" en:  tail -f $LOG_DIR/ui.log
  Inspector de ngrok:                          http://127.0.0.1:4040
  Para bajar todo y restaurar los webhooks:    $0 down

MSG
}

cmd_down() {
    load_env
    twilio_restore_number
    for f in "$NGROK_PID" "$UVICORN_PID"; do
        if pid_alive "$f"; then
            kill "$(cat "$f")" && log "matado pid $(cat "$f") ($(basename "$f" .pid))"
        fi
        rm -f "$f"
    done
    log "abajo"
}

cmd_status() {
    load_env
    if pid_alive "$UVICORN_PID"; then
        log "uvicorn: pid $(cat "$UVICORN_PID")"
    elif port_in_use; then
        log "uvicorn: puerto $PORT ocupado por otro proceso"
    else
        log "uvicorn: no corre"
    fi
    local url
    url="$(ngrok_url)"
    log "ngrok  : ${url:-no corre}"
    log "twilio :"
    twilio_show_number
}

case "${1:-up}" in
    up) cmd_up ;;
    down) cmd_down ;;
    status) cmd_status ;;
    *) die "subcomando desconocido: $1 (up|down|status)" ;;
esac
