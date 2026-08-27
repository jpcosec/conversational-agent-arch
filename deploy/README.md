# Deploy a Modal

Despliega el runtime completo (chat UI, editor de flujo, taxonomía, viz de
embeddings, perfilado y webhook Twilio) como una app serverless en
[Modal](https://modal.com), sirviendo el mismo `frontends.chat.app:create_app`
que corre localmente.

## Qué se empaqueta

- **Código**: `kb_agent/`, `frontends/`, `knowledge_base/`, `project.config.yaml`.
- **KB servida**: `knowledge/` (Antonia — la KB REAL que apunta
  `project.config.yaml: kb_root`), más `tests/knowledge` (Don Peppe, KB de
  prueba, incluida por si se quiere apuntar ahí).
  **No** se copia `tests/knowledge/.embedding_cache` (~600 MB de blobs de un
  modelo de embeddings): `/api/viz/graph` sólo lee embeddings ya calculados
  del frontmatter de cada atom, nunca los recalcula en vivo.
- **Paquetes locales** (no publicados en PyPI, viven en
  `hum-ecosystem/tools/`): `sldb`, `kgdb`, `deskops`. Se copian y se instalan
  con `pip install /root/tools/<paquete>` dentro de la imagen.
- El resto del repo (`desk/`, `runs/`, `.sldb` raíz, `.env`, tests de código,
  etc.) se queda fuera: no lo necesita el runtime para servir.

Ver `deploy/modal_app.py` para el detalle exacto (imagen, ignores, función ASGI).

## Credenciales (Modal Secret)

El runtime usa Vertex AI vía ADC (`google-genai`). Las credenciales viajan por
un [Modal Secret](https://modal.com/docs/guide/secrets) llamado
**`kb-agent-runtime-gcp`**, no horneadas en la imagen.

Crearlo (una sola vez; usa el ADC local ya autenticado):

```bash
modal secret create kb-agent-runtime-gcp \
  GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat ~/.config/gcloud/application_default_credentials.json)" \
  GOOGLE_CLOUD_PROJECT="$(grep '^GOOGLE_CLOUD_PROJECT=' .env | cut -d= -f2-)" \
  GOOGLE_CLOUD_LOCATION=us-central1 \
  GOOGLE_GENAI_USE_VERTEXAI=true
```

Verificar que existe: `modal secret list`.

Dentro de la función ASGI (`serve()` en `deploy/modal_app.py`), al arrancar el
contenedor se escribe `GOOGLE_APPLICATION_CREDENTIALS_JSON` a
`/root/adc.json` y se apunta `GOOGLE_APPLICATION_CREDENTIALS` ahí, antes de
importar `frontends.chat.app`.

### Twilio (opcional)

Si más adelante se activa el canal WhatsApp/SMS y existe un
`TWILIO_AUTH_TOKEN`, crear un segundo secret:

```bash
modal secret create kb-agent-runtime-twilio TWILIO_AUTH_TOKEN=...
```

y agregar `modal.Secret.from_name("kb-agent-runtime-twilio")` a la lista
`secrets=` de la función `serve` en `deploy/modal_app.py`. Hoy no existe y no
se inventó ninguno — `/webhooks/twilio` responde 503 hasta que se configure.

## Deploy

```bash
modal deploy deploy/modal_app.py
```

Para un endpoint de desarrollo separado (app `kb-agent-runtime-dev`, volumen
`kb-agent-runtime-dev-data`, mismo secret GCP) no se copia el archivo: el
nombre sale de la variable `MODAL_APP_NAME`:

```bash
MODAL_APP_NAME=kb-agent-runtime-dev modal deploy deploy/modal_app.py
modal app logs kb-agent-runtime-dev
```

Esto crea (si no existen) la app `kb-agent-runtime` y el Volume persistente
`kb-agent-runtime-data` (montado en `/data` dentro del contenedor), y publica
la función ASGI. La URL pública queda impresa al final del deploy, con forma:

```
https://<workspace>--kb-agent-runtime-serve.modal.run
```

Ver logs en vivo o de la última ejecución:

```bash
modal app logs kb-agent-runtime
```

## Qué persiste en el Volume

`/data/ui-chat.sqlite` es la misma base SQLite que localmente vive en
`runs/ui-chat.sqlite` (`CHAT_DB` = `PROFILING_DB`): sesiones, historial y
`UserTraits` sobreviven a redeploys porque viven en el Volume, no en la
imagen.

Mantenimiento del sqlite del Volume (funciones en `deploy/modal_app.py`,
no en un módulo aparte: Modal solo monta ese archivo y `from deploy... import`
revienta dentro del contenedor):

```bash
modal run deploy/modal_app.py::inspect_db       # solo lectura: tablas, usuarios, primeros mensajes
modal run deploy/modal_app.py::clean_and_seed   # BORRA conversaciones y vuelve a sembrar los usuarios demo
```

## Verificar que está viva

```bash
URL=https://<workspace>--kb-agent-runtime-serve.modal.run

curl -s "$URL/api/health"                  # {"status":"ok","kb_root":".../knowledge",...}
curl -s "$URL/api/config"                  # {"name":"Antonia",...}
curl -s "$URL/api/viz/graph" | head -c 200 # nodes/edges del grafo de embeddings
curl -s "$URL/api/flow" | head -c 200      # grafo de ConversationStep
curl -s -X POST "$URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"que pizzas tienen?","session_id":"smoke"}'
```

## Cambiar de negocio (otra KB)

Una KB = un negocio (ver raíz del README). Para servir otro negocio en Modal:

1. Editar `project.config.yaml` (`kb_root`, `model`, `tools`, marca) — o
   apuntar `PROJECT_CONFIG` a otro yaml y ajustar qué directorio de KB copia
   `deploy/modal_app.py` (`add_local_dir(... "tests/knowledge" ...)`).
2. `modal deploy deploy/modal_app.py` de nuevo.

El Volume (`/data`) no se borra entre redeploys: si se cambia de negocio y se
quiere una sesión/perfilado limpio, hay que rotar `CHAT_DB`/`PROFILING_DB` o
borrar el Volume (`modal volume rm kb-agent-runtime-data` — esto sí es
destructivo).

## Notas de la imagen (qué hubo que ajustar)

- `python_version="3.12"` (el código usa sintaxis 3.10+).
- Versiones de dependencias pineadas a lo que corrió la suite local
  (`pip show sldb kgdb deskops`, `pip freeze`).
- `sldb` usa `markdown-it-py` con la regla `linkify` habilitada, que requiere
  **`linkify-it-py`** como dependencia de import (no está en el
  `pyproject.toml` de `sldb`, pero falla en runtime sin ella con
  `ModuleNotFoundError: Linkify enabled but not installed.`). Se agregó
  explícitamente a `pip_install(...)` en `deploy/modal_app.py`.
- `fastembed`/`torch` **no** son necesarios: el runtime nunca calcula
  embeddings en vivo (ni para chat ni para `/api/viz/graph`), sólo lee los ya
  guardados en el frontmatter de los atoms.
