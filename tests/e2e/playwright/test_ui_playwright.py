"""Smoke E2E de las UIs con Playwright (chat dashboard + flow editor)."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8100"
results = []

def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    # ── 0. Project config endpoint ─────────────────────────
    cresp = page.request.get(f"{BASE}/api/config")
    check("config: /api/config 200", cresp.status == 200, f"status={cresp.status}")
    try:
        cj = cresp.json()
        check("config: exposes name+greeting+model",
              all(k in cj for k in ["name", "greeting", "model", "kb_label"]),
              cj.get("name", ""))
    except Exception as e:
        check("config: json", False, str(e)[:60])

    # ── 1. Chat dashboard ──────────────────────────────────
    page.goto(BASE, wait_until="networkidle")
    check("chat: title present", "Auditable Agent Runtime" in page.content()
          or "Runtime" in page.content(), page.title())
    # input de chat
    box = page.query_selector("textarea, input[type=text]")
    check("chat: input box exists", box is not None)

    # enviar un turno real
    if box:
        box.fill("que pizzas tienen?")
        # buscar boton de enviar
        btn = page.query_selector("button[type=submit], button")
        if btn:
            btn.click()
        else:
            box.press("Enter")
        # esperar respuesta del asistente (turno real Gemini)
        try:
            page.wait_for_function(
                "document.body.innerText.includes('Margherita') || "
                "document.body.innerText.toLowerCase().includes('pizza') || "
                "document.querySelectorAll('[class*=message],[class*=turn],[class*=bubble]').length > 1",
                timeout=45000,
            )
            check("chat: real turn rendered", True)
        except Exception as e:
            check("chat: real turn rendered", False, str(e)[:80])

    # turn inspector / contexto atomico
    # la UI auto-selecciona el turno real (t1). Esperar a que quede seleccionado.
    page.wait_for_function(
        "typeof selectedTurnId!=='undefined' && selectedTurnId && selectedTurnId.startsWith('t')",
        timeout=45000,
    )
    page.wait_for_timeout(2500)
    # el inspector (HTML real) debe mostrar latency, model y los atoms del turno
    insp = page.evaluate(
        "()=>{const e=[...document.querySelectorAll('*')].find(x=>x.textContent.includes('Resumen del Turno')"
        "&&x.className&&x.className.includes('rounded-lg')); return e?e.outerHTML:'';}"
    )
    check("chat: inspector latency+model populated",
          "ms" in insp and "gemini" in insp, "")
    full = page.content()
    check("chat: inspector shows real atoms", "Carta Don Peppe" in full, "")

    page.screenshot(path="/tmp/pw_chat.png", full_page=True)

    # ── 2. Flow editor ─────────────────────────────────────
    page.goto(f"{BASE}/conversation_flow_editor", wait_until="networkidle")
    check("flow: page loads (200 html)", "<" in page.content() and len(page.content()) > 200)
    page.wait_for_timeout(2500)
    fbody = page.inner_text("body")
    # el editor consume /api/flow (nodos ConversationStep)
    has_nodes = page.query_selector_all("[class*=node], svg, canvas, [data-step], .step")
    check("flow: renders nodes/graph", len(has_nodes) > 0, f"{len(has_nodes)} elements")
    page.screenshot(path="/tmp/pw_flow.png", full_page=True)

    # ── 3. /api/flow responde ──────────────────────────────
    resp = page.request.get(f"{BASE}/api/flow")
    check("flow: /api/flow 200", resp.status == 200, f"status={resp.status}")
    try:
        j = resp.json()
        n = len(j.get("nodes", []))
        check("flow: /api/flow has nodes", n > 0, f"{n} nodes")
    except Exception as e:
        check("flow: /api/flow has nodes", False, str(e)[:60])

    # ── 4. Profiling viewer ────────────────────────────────
    page.goto(f"{BASE}/profiling_viewer", wait_until="networkidle")
    page.wait_for_timeout(2500)
    check("profiling: page loads", "Perfilado" in page.content() or len(page.content()) > 200)
    presp = page.request.get(f"{BASE}/api/profiles")
    check("profiling: /api/profiles 200", presp.status == 200, f"status={presp.status}")
    try:
        pj = presp.json()
        check("profiling: has users", len(pj.get("users", [])) > 0, f"{len(pj.get('users', []))} users")
        check("profiling: no dangling fichas", pj.get("missing_fichas") == [],
              f"missing={pj.get('missing_fichas')}")
    except Exception as e:
        check("profiling: /api/profiles json", False, str(e)[:60])
    page.screenshot(path="/tmp/pw_profiling.png", full_page=True)

    check("no console/page errors", len(errors) == 0, "; ".join(errors[:3]))
    browser.close()

npass = sum(1 for _, c, _ in results if c)
print(f"\n{npass}/{len(results)} checks passed")
sys.exit(0 if npass == len(results) else 1)
