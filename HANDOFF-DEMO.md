# Handoff: Demo UI — levantar en worktree `gemini_test-demo`

## Estado actual

Worktree creado en `../gemini_test-demo` con branch `demo` (tracking `origin/task/ui-tidy`).
El branch `demo` tiene las bases de UI unificada: sistema de diseño compartido, navegación única, rutas `/flow`, `/mindmap`, `/users`, placeholder desde config, redirects de rutas viejas.

## Qué hay que hacer

### 1. Crear modo demo en el backend

Agregar un flag `app.demo_mode = True` en el entrypoint de la app FastAPI (`app.py` o similar).
Cuando `demo_mode` está activo:

- **POST `/api/chat`**: no llama al LLM real. Usa el fake LLM de `tests/support/fakes.py` con un state machine determinista que avanza de flow_node según palabras clave del input del usuario.
- **GET `/api/health`**: devuelve `{"status": "ok"}`
- **GET `/api/config`**: devuelve config con `runtime_title: "Demo Agent"`, `input_placeholder: "Escribe algo…"`, labels default
- **GET `/api/taxonomy`**: devuelve un árbol prefabricado con átomos de ejemplo en las 4 familias (self, domain, conversation, user). Al menos 2 ramas con 2-3 atoms cada una.
- **GET `/api/flow`**: devuelve grafo prefabricado con 4-5 ConversationSteps de ejemplo encadenados (bienvenida → consulta → obtencion_datos → tool → despedida).
- **GET `/api/profiles`**: devuelve 3-4 usuarios de ejemplo con traits, eventos, conversaciones sintéticos.
- **GET `/api/tools`**: devuelve 2-3 ToolAtoms de ejemplo.
- **GET `/api/viz/graph`**: devuelve coordenadas PCA simuladas para layout embeddings.
- **GET `/api/atom/{id}`**: devuelve un atom de ejemplo según el ID solicitado.
- **GET `/api/events?user_id=`**: devuelve serie temporal sintética.

### 2. Mock data — archivo separado

Crear `demo_data.py` (o dentro de `frontends/`) con todos los payloads prefabricados.
Importarlos en el backend demo mode.

### 3. Fake LLM — state machine

En `tests/support/fakes.py` ya existe un LLM fake. Adaptarlo para que:
- Reciba el mensaje del usuario
- Según palabras clave, decida un `kind` (`nl`, `tool_call`, `fallback`)
- Avance `flow_node` según una máquina de estados definida en `demo_data.py`
- Devuelva texto coherente con el contexto

### 4. Probar

- Navegar las 4 vistas desde el navegador
- Enviar mensajes en chat → ver el inspector poblado con Context y Razonamiento reales
- Click en atoms → modal funcionando
- Flow: ver grafo, click en nodos → inspector de edición
- Mindmap: toggle árbol/top-down/embeddings
- Users: seleccionar usuario, ver KPIs, traits, eventos, conversaciones

### 5. Cómo levantar

```bash
cd ../gemini_test-demo
# activar entorno virtual
python -m app  # o uvicorn app:app --reload
```

Abrir `http://localhost:XXXX` (puerto que use el proyecto).

## Lo que NO hay que hacer

- No tocar código de producción (solo el flag `demo_mode`)
- No agregar dependencias nuevas
- No modificar tests existentes
- No deployar a ningún lado