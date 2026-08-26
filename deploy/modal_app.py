"""Despliegue del runtime (chat UI + editor de flujo + taxonomia + viz + perfilado +
webhook Twilio) a Modal.

Empaqueta:
  - El codigo de este repo (``kb_agent``, ``frontends``, ``knowledge_base``,
    ``project.config.yaml`` y la KB de prueba ``tests/knowledge``) dentro de la imagen.
  - Los tres paquetes locales (no publicados en PyPI) de los que depende el
    runtime: ``sldb``, ``kgdb``, ``deskops`` (viven en
    ``hum-ecosystem/tools/*``), instalados via ``pip install`` de su
    directorio local dentro de la imagen.

Credenciales: via Modal Secret ``kb-agent-runtime-gcp`` (ADC de Vertex AI +
GOOGLE_CLOUD_PROJECT/LOCATION), NO horneadas en la imagen. Ver deploy/README.md
para como crear el secret.

``create_app()`` (definido en ``frontends.chat.app``) construye el Orchestrator
(SLDB reader + KGDB + cliente genai) en cada arranque de contenedor -- no al
importar el modulo -- asi que es seguro invocarlo dentro de la funcion ASGI.

Uso:
    modal deploy deploy/modal_app.py
    modal app logs kb-agent-runtime
"""
from __future__ import annotations

from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_ROOT = Path("/home/jp/proyectos/hum-ecosystem/tools")

APP_NAME = "kb-agent-runtime"
VOLUME_NAME = "kb-agent-runtime-data"
GCP_SECRET_NAME = "kb-agent-runtime-gcp"
#: Secret opcional con TWILIO_AUTH_TOKEN para /webhooks/twilio. No existe hoy
#: (no se invento uno); si se crea mas adelante, agregar
#: `modal.Secret.from_name("kb-agent-runtime-twilio")` a la lista `secrets=`
#: de la funcion `serve` de abajo y redeployar.

REMOTE_APP_DIR = "/root/app"

#: Excludes comunes para los paquetes locales (sldb, kgdb, deskops): solo
#: necesitamos el codigo fuente instalable, no su workflow/tests/docs propios.
_TOOL_IGNORE = [
    ".git",
    ".git/**",
    "**/__pycache__",
    "**/__pycache__/**",
    "dist",
    "dist/**",
    "build",
    "build/**",
    "desk",
    "desk/**",
    "docs",
    "docs/**",
    "tests",
    "tests/**",
    "*.html",
    "**/*.html",
    ".venv",
    ".venv/**",
    "*.egg-info",
    "*.egg-info/**",
    "runs",
    "runs/**",
]

_PYCACHE_IGNORE = ["**/__pycache__", "**/__pycache__/**"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Runtime deps del repo, pineados a lo que corrio la suite local
        # (ver `pip freeze` / pip show sldb kgdb deskops).
        "fastapi==0.135.2",
        "starlette==1.3.1",
        "uvicorn[standard]==0.42.0",
        "python-multipart==0.0.26",
        "twilio==9.10.9",
        "python-dotenv==1.0.1",
        "google-genai==2.9.0",
        "networkx==3.6.1",
        "numpy==2.1.3",
        "PyYAML==6.0.3",
        "markdown-it-py==4.0.0",
        "linkify-it-py==2.0.0",
        "mdit-py-plugins==0.5.0",
        "Jinja2==3.1.6",
        "SQLAlchemy==2.0.49",
        "pydantic==2.13.4",
    )
    # Paquetes locales (no en PyPI): copian el codigo fuente y se instalan
    # via pip contra el directorio local (usa su pyproject.toml).
    .add_local_dir(str(TOOLS_ROOT / "sldb"), "/root/tools/sldb", copy=True, ignore=_TOOL_IGNORE)
    .add_local_dir(str(TOOLS_ROOT / "kgdb"), "/root/tools/kgdb", copy=True, ignore=_TOOL_IGNORE)
    .add_local_dir(str(TOOLS_ROOT / "deskops"), "/root/tools/deskops", copy=True, ignore=_TOOL_IGNORE)
    .run_commands("pip install /root/tools/sldb /root/tools/kgdb /root/tools/deskops")
    # Codigo + KB de este repo. Copias selectivas (en vez de todo el repo) para
    # no arrastrar desk/, runs/, .sldb raiz, ni el cache de embeddings (~600MB
    # de blobs de modelo que el runtime no necesita: /api/viz/graph lee
    # embeddings YA calculados del frontmatter de los atoms).
    .add_local_dir(str(REPO_ROOT / "kb_agent"), f"{REMOTE_APP_DIR}/kb_agent", copy=True,
                    ignore=[*_PYCACHE_IGNORE, ".adk", ".adk/**"])
    .add_local_dir(str(REPO_ROOT / "frontends"), f"{REMOTE_APP_DIR}/frontends", copy=True,
                    ignore=_PYCACHE_IGNORE)
    .add_local_dir(str(REPO_ROOT / "knowledge_base"), f"{REMOTE_APP_DIR}/knowledge_base", copy=True,
                    ignore=_PYCACHE_IGNORE)
    .add_local_dir(str(REPO_ROOT / "tests" / "knowledge"), f"{REMOTE_APP_DIR}/tests/knowledge", copy=True,
                    ignore=[*_PYCACHE_IGNORE, ".embedding_cache", ".embedding_cache/**", "desk", "desk/**"])
    .add_local_dir(str(REPO_ROOT / "tests" / "knowledge_antonia"), f"{REMOTE_APP_DIR}/tests/knowledge_antonia",
                    copy=True, ignore=_PYCACHE_IGNORE)
    .add_local_file(str(REPO_ROOT / "project.config.yaml"), f"{REMOTE_APP_DIR}/project.config.yaml", copy=True)
)

app = modal.App(APP_NAME)
data_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


@app.function(
    image=image,
    volumes={"/data": data_volume},
    secrets=[modal.Secret.from_name(GCP_SECRET_NAME)],
    min_containers=1,
    timeout=600,
)
@modal.asgi_app()
def serve():
    import os
    import sys

    if REMOTE_APP_DIR not in sys.path:
        sys.path.insert(0, REMOTE_APP_DIR)
    os.chdir(REMOTE_APP_DIR)

    # ADC de Vertex AI: el secret trae el JSON como string; lo materializamos
    # a un archivo y apuntamos GOOGLE_APPLICATION_CREDENTIALS a el (en vez de
    # hornear el archivo en la imagen).
    adc_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if adc_json:
        adc_path = "/root/adc.json"
        with open(adc_path, "w", encoding="utf-8") as fh:
            fh.write(adc_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path

    os.environ["PROJECT_CONFIG"] = f"{REMOTE_APP_DIR}/project.config.yaml"
    os.environ["CHAT_DB"] = "/data/ui-chat.sqlite"
    os.environ["PROFILING_DB"] = "/data/ui-chat.sqlite"
    os.environ["PYTHONPATH"] = REMOTE_APP_DIR

    from frontends.chat.app import create_app

    return create_app()
