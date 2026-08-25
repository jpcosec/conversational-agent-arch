"""Corrida REAL end-to-end: pizzeria Don Peppe.

Integra los modulos reales (SIN mock, SIN dummy, SIN stub):
  SLDBReader real -> ContextCompiler real -> Conversador (Gemini real via Vertex ADC)

Niveles recuperados de la estrategia de testing:
  Nivel 2: fallback estricto contra LLM real
  Nivel 3: subgrafo REAL en SLDB (.sldb_e2e_donpeppe)
  Nivel 4: golden transcript real de 3 turnos

Uso: python tests/e2e/run_donpeppe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.agent import CANONICAL_FALLBACK_RESPONSE, draft_conversador_response
from kb_agent.ontologizador.compiler import ContextCompiler
from kb_agent.ontologizador.sldb_reader import SLDBReader

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
MODEL = "gemini-2.5-flash"

_client = genai.Client()


def conversador_nl(compiled: dict) -> str:
    """Redacta NL con Gemini REAL, estrictamente grounded en el contexto."""
    facts = [f["body"] for f in compiled.get("domain_facts", [])]
    rules = [r["body"] for r in compiled.get("rules", [])]
    grounding = "\n".join(f"- {t}" for t in facts + rules)
    prompt = (
        "Eres el asistente de la pizzeria Don Peppe. Responde en espanol, "
        "breve y amable, usando EXCLUSIVAMENTE los datos de abajo. "
        "No inventes nada fuera de estos datos.\n\n"
        f"DATOS:\n{grounding}\n\n"
        f"PREGUNTA: {compiled['question']}\n\nRESPUESTA:"
    )
    resp = _client.models.generate_content(model=MODEL, contents=prompt)
    return (resp.text or "").strip()


def run_turn(compiler: ContextCompiler, question: str, scenario: str) -> dict:
    compiled = compiler.compile(question=question, user_id=None, scenario=scenario)
    decision = draft_conversador_response(compiled)

    if isinstance(decision, dict) and "function_call" in decision:
        kind, reply = "tool_call", decision
    elif decision == CANONICAL_FALLBACK_RESPONSE:
        kind, reply = "fallback", decision
    else:
        # grounding disponible -> redacta NL real con Gemini
        kind, reply = "nl", conversador_nl(compiled)

    return {
        "question": question,
        "scenario": scenario,
        "is_empty": compiled["is_empty"],
        "kind": kind,
        "reply": reply,
    }


def main() -> int:
    reader = SLDBReader(kb_root=STORE_ROOT, store_name=".sldb")
    compiler = ContextCompiler(reader=reader)

    transcript = []
    print("=" * 70)
    print("CORRIDA REAL E2E — Pizzeria Don Peppe (Gemini real, SLDB real)")
    print("=" * 70)

    # Turno 1 — dato real del KB
    t1 = run_turn(compiler, "A que hora abren el sabado?", "pizzeria")
    transcript.append(t1)
    print(f"\n[T1 in-domain] {t1['question']}")
    print(f"  kind={t1['kind']} is_empty={t1['is_empty']}")
    print(f"  reply: {t1['reply']}")

    # Turno 2 — fuera de dominio -> fallback canonico
    t2 = run_turn(compiler, "Tienen sucursal en Paris?", "paris")
    transcript.append(t2)
    print(f"\n[T2 out-domain] {t2['question']}")
    print(f"  kind={t2['kind']} is_empty={t2['is_empty']}")
    print(f"  reply: {t2['reply']}")

    # Turno 3 — tool call estructurado real
    t3 = run_turn(
        compiler,
        "Quiero reservar mesa para 4 personas el viernes a las 20:00 a nombre de Rojas",
        "pizzeria",
    )
    transcript.append(t3)
    print(f"\n[T3 tool-call] {t3['question']}")
    print(f"  kind={t3['kind']}")
    print(f"  reply: {json.dumps(t3['reply'], ensure_ascii=False)}")

    # === ASERCIONES DURAS ===
    print("\n" + "=" * 70)
    print("ASERCIONES")
    print("=" * 70)
    failures = []

    # T1: debe ser NL real con horario del KB (19:00 y 23:30)
    if t1["kind"] != "nl":
        failures.append(f"T1 esperaba kind=nl, obtuvo {t1['kind']}")
    if "19" not in t1["reply"]:
        failures.append(f"T1 no cita el horario real de apertura del KB (19:00): {t1['reply']!r}")

    # T2: fallback canonico exacto
    if t2["kind"] != "fallback" or t2["reply"] != CANONICAL_FALLBACK_RESPONSE:
        failures.append(f"T2 esperaba fallback canonico exacto, obtuvo {t2['reply']!r}")

    # T3: function_call estructurado real name=crear_reserva, personas=4
    if t3["kind"] != "tool_call":
        failures.append(f"T3 esperaba tool_call, obtuvo {t3['kind']}: {t3['reply']!r}")
    else:
        fc = t3["reply"]["function_call"]
        if fc["name"] != "crear_reserva":
            failures.append(f"T3 name esperado crear_reserva, obtuvo {fc['name']}")
        if fc["args"].get("personas") != 4:
            failures.append(f"T3 personas esperado 4, obtuvo {fc['args'].get('personas')}")

    # Guardar transcript real como evidencia
    out_dir = PROJECT_ROOT / "runs" / "e2e"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "donpeppe-transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nTranscript real guardado en {out_dir / 'donpeppe-transcript.json'}")

    if failures:
        print("\nRESULTADO: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nRESULTADO: PASS — 3 turnos reales verdes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
