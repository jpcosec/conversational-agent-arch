# Operaciones, Testing y Gobernanza

### Estrategia de Testing de 4 Capas
Suite de pruebas dividida en Unit (lógica pura y orquestador con LLM inyectado fake), Integration (API y flujos), E2E (smoke tests con Gemini real y harness de simulación Agente-vs-Agente), y UI (Playwright). Todo test aísla el estado usando la KB de pruebas y una base SQL efímera.

### Topología de Despliegue (Modal)
Despliegue serverless en Modal (`deploy/modal_app.py`). El runtime completo (ASGI de FastAPI sirviendo las 5 UIs y los endpoints webhooks) se empaqueta junto con la Base de Conocimiento activa y se expone a internet, escalando desde cero.

### Gobernanza Deskops
El repositorio se gobierna a sí mismo utilizando el directorio `desk/`. Las tareas, rituales (ej. closeout, handoff), y la arquitectura visual (spec2viz) se documentan como átomos de estado, permitiendo a subagentes LLM leer y operar sobre el repositorio de forma autónoma y determinista.

### Migraciones de Base de Datos (Alembic)
El schema SQL vive en `kb_agent/models_sql/` (una sola `Base` declarativa: `identity.py` la define, `session.py`/`reservas.py`/`recordatorios.py` la importan). El `Orchestrator` corre `Base.metadata.create_all()` al arrancar, y eso **crea tablas que faltan pero nunca altera una tabla existente** — si un modelo gana o cambia una columna, una base vieja se queda atrás en silencio y explota recién en el primer INSERT/SELECT real con un `OperationalError: no such column: ...` opaco (así se descubrió el problema: en `runs/local-chat.sqlite` faltaban `flow_node`/`flow_slots` de `SessionState` tras el commit que las agregó). Por eso el schema se versiona con [Alembic](https://alembic.sqlalchemy.org/) (`alembic/`, `alembic.ini`).

`alembic/env.py` no hardcodea la URL de la base: la resuelve en runtime con la misma precedencia que el resto del runtime (`kb_agent/project_config.py`) — `DATABASE_URL` (env, URL completa) > `CHAT_DB` (env, path a sqlite) > `project.config.yaml` / defaults de `ProjectConfig`. También expone el `target_metadata` combinado (importa `identity`, `session`, `reservas` y `recordatorios` para que sus tablas queden registradas en la única `Base.metadata`) y habilita `render_as_batch=True`, imprescindible porque SQLite no soporta `ALTER COLUMN` nativo — Alembic lo emula recreando la tabla.

**Crear una migración nueva** (después de tocar un modelo en `kb_agent/models_sql/`):
```
DATABASE_URL="sqlite:////ruta/a/una/base/vacia/o/de/prueba.sqlite" \
  python -m alembic revision --autogenerate -m "descripción corta"
```
Nunca apuntar el autogenerate a `runs/local-chat.sqlite` ni a ninguna base con datos reales: el autogenerate compara el modelo contra ESA base y conviene que arranque vacía o ya al día. Siempre revisar a mano el archivo generado en `alembic/versions/` antes de commitear — el autogenerate a veces mete ruido (constraints o índices que no corresponden).

**Aplicar migraciones pendientes:**
```
CHAT_DB=runs/local-chat.sqlite python -m alembic upgrade head
```
(o `DATABASE_URL=sqlite:///runs/local-chat.sqlite ...`; sin ninguna de las dos, toma la base resuelta por `project.config.yaml`).

**Base preexistente que ya tiene el esquema al día** (por ejemplo una base creada con `create_all()` antes de que existieran las migraciones, como `runs/local-chat.sqlite`): no correr `upgrade`: al no tener `alembic_version`, intentaría recrear tablas que ya existen y fallaría. Marcarla como al día sin ejecutar DDL:
```
CHAT_DB=runs/local-chat.sqlite python -m alembic stamp head
```

**Chequeo automático al arrancar:** `kb_agent/cli.py` llama a `kb_agent.db_check.check_db_revision()` antes de crear el `Orchestrator` y, si la base no está en `head` (o no tiene `alembic_version`), imprime un `[WARNING]` con el diagnóstico y el comando a correr — nunca frena el arranque ni lanza excepción.

