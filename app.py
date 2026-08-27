from __future__ import annotations

from dotenv import load_dotenv

from kb_agent.project_config import load_project_config
from frontends.chat.app import create_app

load_dotenv()
CFG = load_project_config()
app = create_app(CFG)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=CFG.host, port=CFG.port)
