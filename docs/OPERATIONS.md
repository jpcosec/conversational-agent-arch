# Operaciones, Testing y Gobernanza

### Estrategia de Testing de 4 Capas
Suite de pruebas dividida en Unit (lógica pura y orquestador con LLM inyectado fake), Integration (API y flujos), E2E (smoke tests con Gemini real y harness de simulación Agente-vs-Agente), y UI (Playwright). Todo test aísla el estado usando la KB de pruebas y una base SQL efímera.

### Topología de Despliegue (Modal)
Despliegue serverless en Modal (`deploy/modal_app.py`). El runtime completo (ASGI de FastAPI sirviendo las 5 UIs y los endpoints webhooks) se empaqueta junto con la Base de Conocimiento activa y se expone a internet, escalando desde cero.

### Gobernanza Deskops
El repositorio se gobierna a sí mismo utilizando el directorio `desk/`. Las tareas, rituales (ej. closeout, handoff), y la arquitectura visual (spec2viz) se documentan como átomos de estado, permitiendo a subagentes LLM leer y operar sobre el repositorio de forma autónoma y determinista.

