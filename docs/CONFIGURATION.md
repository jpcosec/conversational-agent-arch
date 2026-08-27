# Configuración del runtime

> Cómo está organizada la configuración de este chatbot y qué mover para
> montar **otro negocio** (otra KB, otro endpoint Modal).

## Doctrina

Una KB = un negocio. La configuración vive en **tres capas**, no en el código:

| Capa | Dónde vive | Qué contiene |
|------|-----------|--------------|
| **KB** (`.sldb`) | `knowledge/` (store del negocio) | Todo lo que **dice o instruye un LLM**: hechos, reglas, identidad, flujo, y el **encuadre de cada agente**. |
| **YAML** | `project.config.yaml` | Valores y parámetros: marca, rutas, modelo, tuning del runtime, infra de deploy. |
| **Runtime** | código (`kb_agent/`) | Mecánica fija del sistema: los 11 tipos de documento, la máquina de estados, los contratos de tags. **No es config.** |

Regla de oro: si es **texto que lee/escribe un LLM**, va a la KB. Si es un
**valor/parámetro/dirección**, va al YAML. Si es **mecánica del runtime**, se
queda en el código.

---

## Capa 1 — Prompts y texto LLM (KB)

Los 4 agentes LLM (Conversador, Ruteador, Orquestador, Gate) arman su prompt en
**dos capas**:

- **Doctrina** (fija, en el código): familias de documentos, regla de oro,
  formato de salida. No cambia por negocio. Vive en las funciones `render_*`
  de `kb_agent/agents/` (`render_gate_criteria`, `render_router_instruction`,
  `render_orchestrator_flow`).
- **Encuadre** (por negocio, en la KB): quién es cada agente **en este
  negocio** ("gate regulatorio de un programa de farmacovigilancia") y los
  ejemplos de dominio.

### Modelo `AgentFraming` (familia `agent`)

El encuadre vive como un documento SLDB tipado, indexado por **rol**:

- Modelo: `kb_agent/models/knowledge/agent_framing.py`
- Roles válidos (`kb_agent.agents.base.AgentRole`):
  `conversador` | `router` | `orchestrator` | `gate`
- Campos: `role`, `framing` (lead-in del prompt), `examples` (opcional).

El runtime lo carga en `Orchestrator._load_agent_framing(role)` y lo inyecta al
`render_*` correspondiente. **Sin un `AgentFraming` para un rol, el agente cae a
un encuadre genérico neutro** (sin vocabulario de ningún negocio).

Documentos de ejemplo en la KB de Antonia:
- `knowledge/atoms/agent-antonia-gate.md` (encuadre de farmacovigilancia)
- `knowledge/atoms/agent-antonia-router.md` (ejemplos clínicos del ruteador)

### Identidad y fallback

- Identidad del agente → `SelfDeclaration` (familia `self`). El código solo
  tiene un `_IDENTITY_LAST_RESORT` genérico por si la KB no la declara.
- Mensaje de fallback → `FallbackRule` (familia `conversation`), o
  `project.config.yaml: fallback_message`. El código solo tiene un
  `DEFAULT_FALLBACK_MESSAGE` genérico de último recurso.

---

## Capa 2 — Config y parámetros (YAML)

Todo en `project.config.yaml`, bajo `project:`. Cada valor admite override por
variable de entorno.

### Bloques

| Bloque | Campos | Override env |
|--------|--------|--------------|
| Identidad | `name`, `slug` | — |
| KB | `kb_root`, `test_kb_root` | `KB_ROOT` |
| DBs | `chat_db`, `profiling_db` | `CHAT_DB`, `PROFILING_DB` |
| LLM | `model` | `GEMINI_MODEL` |
| Fallback | `fallback_message` | — |
| Tools | `tools:` (nombre → `modulo:funcion`) | — |
| `server` | `host`, `port` | `HOST`, `PORT` |
| `ui` | `runtime_title`, `kb_label`, `greeting`, `input_placeholder` | — |
| `tuning` | `max_bundle_size`, `history_limit`, `router_max_results`, `tool_timeout_ms` | `MAX_BUNDLE_SIZE`, `HISTORY_LIMIT`, `ROUTER_MAX_RESULTS`, `TOOL_TIMEOUT_MS` |
| `deploy` | `modal_app_name`, `gcp_secret_name`, `twilio_secret_name`, `min_containers`, `serve_timeout_s` | `MODAL_APP_NAME` |

### `tuning` — parámetros del runtime

Antes eran constantes hardcodeadas. Hoy salen del YAML (`ProjectConfig.tuning`):

- `max_bundle_size`: tope de documentos en el bundle del turno
  (`ContextCompiler`).
- `history_limit`: mensajes recientes que entran al contexto.
- `router_max_results`: default de `explore_multi` del ruteador.
- `tool_timeout_ms`: timeout de una tool call (`RouterStateMachine`).

### `deploy` — infra de Modal

Antes hardcodeada en `deploy/modal_app.py`. Hoy sale del YAML
(`ProjectConfig.deploy`), leída por `modal_app.py` al importar:

- `modal_app_name`: nombre de la app **y** del volumen (`<app>-data`).
  `MODAL_APP_NAME` sigue teniendo prioridad.
- `gcp_secret_name`: Modal Secret con el ADC de Vertex AI.
- `twilio_secret_name`: Secret con `TWILIO_AUTH_TOKEN` (o `null` → la ruta
  `/webhooks/twilio` responde 503 hasta configurarlo).
- `min_containers`, `serve_timeout_s`: parámetros del `serve`.

---

## Capa 3 — Runtime (NO tocar)

Mecánica del sistema. No es configuración; no se mueve a KB ni YAML.

- Los 11 tipos de documento (`_MODEL_TYPES` / `_MODEL_CLS_BY_TIPO` en
  `compiler.py`; `gate.py` como 11.º).
- La máquina de estados (`RouterNode`, `BREAKPOINT_MISS`, ...).
- El contrato de tag del piso de seguridad
  (`_SECURITY_FLOOR_TAG = "conversation:security"`). El **contenido** del piso
  vive en la KB como `RuleAtom`; el tag es convención fija.
- Los verbos de acción del pre-filtro del gate (`_ACTION_VERBS_AR`) y las
  heurísticas léxicas de intención de tool. Son español + verbos fijos; una KB
  con otro dominio de acciones (p.ej. "cotizar", "facturar") debe extenderlos
  en el código, a conciencia.

---

## Montar otro negocio (checklist)

Para una KB nueva en **otro endpoint Modal separado** (patrón: una rama = un
negocio):

1. **KB store** — construir `knowledge/` con los atoms del negocio, incluyendo
   sus `AgentFraming` (gate/router al menos) para que los prompts no hablen del
   negocio anterior.
   - Registrar el modelo si el store es nuevo:
     `sldb models add AgentFraming --store knowledge/.sldb --pythonpath .`

2. **`project.config.yaml`** — ajustar:
   - Identidad (`name`, `slug`), `ui.*`, `greeting`.
   - `kb_root` → store del negocio.
   - `tools:` → handlers que la KB declare.
   - `tuning:` si el negocio necesita otros topes.
   - `deploy.modal_app_name` → nombre de la app/volumen propios.
   - `deploy.gcp_secret_name` / `twilio_secret_name` → secrets propios si aplica.

3. **Deploy** — `modal deploy deploy/modal_app.py`.
   - App y volumen salen del YAML (o de `MODAL_APP_NAME`).
   - No hay que editar `modal_app.py`: lee la infra del YAML.

4. **Verificar** — sin credenciales:
   `SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q`
   y `sldb stores check --store knowledge/.sldb`.

### Qué NO se toca al cambiar de negocio

- `kb_agent/` (runtime, agentes, compilador, gate).
- Las funciones `render_*` (doctrina de los prompts).
- Los 11 tipos de documento.
- `deploy/modal_app.py` (ya lee todo del YAML).
