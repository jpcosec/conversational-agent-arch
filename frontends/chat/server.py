"""Entrypoint del servidor HTTP del runtime.

Uso:
  uvicorn frontends.chat.server:app --reload
  # o: python -m frontends.chat.server   (host/port desde project.config.yaml o HOST/PORT)

La app se construye en ``frontends.chat.app.create_app``; este modulo solo carga
``.env``, la config del negocio y expone ``app`` para uvicorn.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.project_config import load_project_config  # noqa: E402
from frontends.chat.app import create_app  # noqa: E402

CFG = load_project_config()
app = create_app(CFG)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=CFG.host, port=CFG.port)


if __name__ == "__main__":
    main()
