<!-- generado desde desk/bundles/bundle-glosario.md — no editar a mano; python desk/bundles/materialize.py -->
# Glosario de Conceptos

Definiciones de los términos ubicuos (Ubiquitous Language) utilizados en todo el ecosistema de KB Agent.

### Turno Extendido
El ciclo de vida completo de un mensaje de usuario. A diferencia de un request/response tradicional, el turno extendido incluye pausas en la ejecución síncrona para ejecutar herramientas externas (tools) y procesos asíncronos posteriores a la respuesta (como la extracción de perfiles y la reflexión en batch).

### Átomo Semántico (SLDB)
Unidad mínima de conocimiento y gobernanza. Técnicamente es un archivo Markdown con frontmatter YAML (formato SLDB). Todo en el sistema es un átomo: las reglas de negocio, los perfiles de usuario, los pasos del flujo, e incluso la propia documentación de arquitectura.

### Negocios Activos (KBs)
El sistema soporta múltiples negocios aislados. Actualmente conviven dos KBs principales: 'Antonia' (asistente clínico, producción) que vive en `knowledge/`, y 'Don Peppe' (pizzería, pruebas) que vive en `tests/knowledge/`. El archivo `project.config.yaml` actúa como el switch que define cuál está activo.

### Encuadre de agentes desde la KB (AgentFraming)
Porque una KB = un negocio y el código no puede hardcodear el dominio. Cada agente LLM arma su prompt en dos capas — la doctrina (mecánica fija del runtime — familias, regla de oro, formato de salida) vive en las funciones `render_*` de `kb_agent/agents/` (`render_gate_criteria`, `render_router_instruction`, `render_orchestrator_flow`) y se mantiene business-neutral; el encuadre (quién es este agente EN ESTE negocio, más ejemplos de dominio) vive en la KB como documento tipado `AgentFraming` (kb_agent/models/knowledge/agent_framing.py, familia `agent`, campos `role`, `framing`, `examples`). Los roles válidos son el enum `AgentRole` de kb_agent/agents/base.py (`conversador` | `router` | `orchestrator` | `gate`), único punto de verdad de qué agentes existen. El Orquestador carga el encuadre por rol en `Orchestrator._load_agent_framing(role)` y lo inyecta como lead-in al `render_*` correspondiente; sin `AgentFraming` para un rol, el agente cae a un encuadre genérico neutro. Ejemplos en la KB de Antonia — knowledge/atoms/agent-antonia-gate.md (gate regulatorio de farmacovigilancia) y agent-antonia-router.md (ejemplos clínicos del ruteador). Detalle en docs/CONFIGURATION.md.

### Modo demo
Modo opt-in del runtime que sirve las 4 vistas sin orquestador ni LLM. Se activa con `DEMO_MODE=1` y lo resuelve `ProjectConfig.demo_mode` (kb_agent/project_config.py) — nunca se enciende en modo test (`resolved_mode != "test"`) ni se setea en producción. Con el flag activo, `create_app` (frontends/chat/app.py) no exige Orchestrator y todos los `/api/*` responden datos prefabricados de `frontends/chat/demo_data.py` (config, atoms, flow, usuarios, perfiles); el chat usa `DemoStateMachineConversador`, una máquina de estados determinista (saludo -> consulta -> obtencion_datos -> tool_call) que imita al Conversador. Sobre las 4 vistas corre `frontends/shared/demo-tour.js`, un único recorrido guiado con cuadros que apuntan a elementos por `data-testid`, navega solo de vista en vista y guarda el progreso en localStorage (`demo-tour-idx`, `demo-tour-done`). Lo verifica tests/ui/test_demo_e2e.py (Playwright, marker `ui`, sin credenciales).
