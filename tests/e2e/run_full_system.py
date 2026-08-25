"""Corrida REAL del SISTEMA COMPLETO cableado — Don Peppe.

Prueba que TODO esta conectado de verdad:
  Router -> Ontologizador (con traits del user) -> Conversador (Gemini)
        -> Tool dispatcher REAL (persiste reserva en SQL)
        -> ChatHistory scrubbed -> Perfilador async (Gemini) -> traits en SQL
        -> el siguiente turno USA el perfil recien aprendido

SIN mock. LLM real (Vertex ADC), SQL real, SLDB real.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.orchestrator import Orchestrator

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
USER = "wa:+56911111111"


def main() -> int:
    orch = Orchestrator(kb_root=STORE_ROOT)
    transcript = []
    failures = []

    print("=" * 70)
    print("  SISTEMA COMPLETO CABLEADO — Don Peppe (Gemini + SQL + SLDB reales)")
    print("=" * 70)

    def turn(msg: str, scenario: str = "pizzeria") -> dict:
        r = orch.handle_turn(external_id=USER, message=msg, scenario=scenario)
        transcript.append(r)
        print(f"\n[{r['kind']}] Tu > {msg}")
        reply = json.dumps(r["reply"], ensure_ascii=False) if isinstance(r["reply"], dict) else r["reply"]
        print(f"  Bot > {reply}")
        print(f"  traits_en_contexto={r['used_traits_in_context']} | traits_after={r['traits_after']}")
        if r["system_turn"]:
            print(f"  [SYSTEM TURN persistido] {json.dumps(r['system_turn'], ensure_ascii=False)}")
        return r

    # ── Turno 1: el cliente revela un trait. Aun no hay perfil en contexto.
    t1 = turn("Hola, soy vegetariano. Que pizzas me recomiendan?")
    if "trait-vegetariano" not in t1["traits_after"]:
        failures.append("T1: el perfilador NO aprendio trait-vegetariano del mensaje real")
    if t1["used_traits_in_context"]:
        failures.append("T1: no deberia haber traits en contexto todavia (primer turno)")

    # ── Turno 2: pregunta neutra. El PERFIL ya aprendido debe entrar al contexto.
    t2 = turn("Que me recomiendan para hoy?")
    if "trait-vegetariano" not in t2["used_traits_in_context"]:
        failures.append("T2: el perfil vegetariano NO se inyecto en el contexto del turno siguiente")

    # ── Turno 3: fuera de dominio -> fallback canonico
    t3 = turn("Tienen sucursal en Tokio?", scenario="tokio")
    from kb_agent.agent import CANONICAL_FALLBACK_RESPONSE
    if t3["reply"] != CANONICAL_FALLBACK_RESPONSE:
        failures.append(f"T3: esperaba fallback canonico, obtuvo {t3['reply']!r}")

    # ── Turno 4: reserva real -> tool dispatcher PERSISTE en SQL
    t4 = turn("Quiero reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas")
    if t4["kind"] != "tool_call":
        failures.append(f"T4: esperaba tool_call, obtuvo {t4['kind']}")
    elif not t4["system_turn"] or t4["system_turn"].get("status") != "ok":
        failures.append(f"T4: la reserva NO se persistio: {t4['system_turn']}")

    # ── Verificacion de persistencia real en SQL
    n_reservas = orch.count_reservas()
    print("\n" + "=" * 70)
    print(f"Reservas persistidas en SQL: {n_reservas}")
    if n_reservas != 1:
        failures.append(f"Persistencia: esperaba 1 reserva en SQL, hay {n_reservas}")

    out_dir = PROJECT_ROOT / "runs" / "e2e"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "full-system-transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"Transcript guardado en {out_dir / 'full-system-transcript.json'}")

    print("\n" + "=" * 70)
    if failures:
        print("RESULTADO: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULTADO: PASS — sistema completo cableado, perfil vivo + reserva persistida")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
