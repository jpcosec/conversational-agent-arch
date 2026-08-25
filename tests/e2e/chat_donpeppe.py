"""Chat interactivo REAL con Don Peppe (SLDB real + Gemini real).

Uso: python tests/e2e/chat_donpeppe.py
Escribe 'salir' para terminar.
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


def main() -> int:
    reader = SLDBReader(kb_root=STORE_ROOT, store_name=".sldb")
    compiler = ContextCompiler(reader=reader)

    print("=" * 60)
    print("  Pizzeria Don Peppe — chat real (Gemini + SLDB)")
    print("  Escribe 'salir' para terminar.")
    print("=" * 60)

    while True:
        try:
            msg = input("\nTu > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nChau!")
            return 0
        if not msg or msg.lower() in {"salir", "exit", "quit"}:
            print("Chau!")
            return 0

        compiled = compiler.compile(question=msg, user_id=None, scenario="pizzeria")
        decision = draft_conversador_response(compiled)

        if isinstance(decision, dict) and "function_call" in decision:
            fc = decision["function_call"]
            print(f"Bot > [TOOL] {fc['name']}({json.dumps(fc['args'], ensure_ascii=False)})")
        elif decision == CANONICAL_FALLBACK_RESPONSE:
            print(f"Bot > {decision}")
        else:
            print(f"Bot > {conversador_nl(compiled)}")


if __name__ == "__main__":
    raise SystemExit(main())
