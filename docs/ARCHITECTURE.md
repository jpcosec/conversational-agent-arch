# Arquitectura del Sistema

Esta documentación está ensamblada a partir de los Átomos Semánticos del proyecto, garantizando que el diseño arquitectónico mantenga cero-drift con el código real.

> **Catálogo Visual Spec2Viz**: `desk/spec2viz/build/architecture.html`

## El Motor Conversacional Síncrono (Runtime)
### Canales de Entrada
Múltiples interfaces de conexión que convergen en el Orquestador. Incluyen el endpoint principal FastAPI (`POST /api/chat`), el webhook de WhatsApp/SMS de Twilio, y el intérprete local interactivo CLI. Todo canal expone un `external_id`.

### Orquestador (Hub Central)
Punto de entrada unificado (`Orchestrator.handle_turn`). Instancia la sesión SQL, inicializa el RouterStateMachine, delega la decisión a la policy pura, ejecuta las tool calls locales, delega la redacción al Conversador, persiste el historial purgado en SQL, y dispara asíncronamente al Perfilador a través del Event Bus.

### PII Scrubber
Capa de interceptación de privacidad. El Orquestador lo invoca para enmascarar (scrub) todo contenido antes de persistirlo en el historial SQL (`ChatHistory`) y antes de publicarlo en el EventBus, asegurando aislamiento absoluto de datos personales.

### Router State Machine
Máquina de estados técnica (`RouterStateMachine`) con 6 nodos (IDLE, BUFFERING, EVALUATING_CONTEXT, DRAFTING_RESPONSE, WAITING_TOOL, BREAKPOINT_MISS). Rutea la petición hacia el Ontologizador y pausa la ejecución síncrona en `WAITING_TOOL` mientras el Orquestador ejecuta una herramienta.

### Ontologizador (Context Compiler)
Motor de compilación determinista. Lee TODA la base de conocimiento tipada (los 10 modelos) desde SLDB, y extrae el nodo actual del grafo de ConversationStep (desde KGDB) para ensamblar el `CompiledDocument` que representa el estado exacto y los hechos relevantes para el turno.

### Policy Pura (decide_turn)
Función de evaluación pura (`decide_turn`) sin estado ni I/O. Analiza el contexto compilado y determina estrictamente la acción a seguir devolviendo un `kind`: `tool_call` (si hay intención y parámetros válidos), `fallback` (si falta grounding o el contexto está vacío), o `nl` (lenguaje natural).

### Tool Handlers y Registry
Mecanismo de ejecución de acciones. Las tools son funciones locales de Python (`crear_reserva`, `agendar_recordatorio`) mapeadas en el `project.config.yaml`. Cuando la policy decide ejecutarlas, el Orquestador llama al handler, el cual típicamente muta estado relacional (tablas SQL de negocio).

### Agente Conversador
Motor generativo de lenguaje natural (`GeminiConversador`). Recibe el contexto validado (y el resultado de una tool si la hubo) y redacta la respuesta final usando el LLM externo. No alucina ni toma decisiones de flujo; obedece la identidad, estilo y límites provistos por el Ontologizador.


## Procesos Offline y Asíncronos
### InProcess Event Bus
Canal de mensajería in-memory que desacopla el cierre del turno síncrono del perfilado asíncrono. El Orquestador publica el turno aquí (`publish_turn_closed`), momento en el cual se aplica el enmascaramiento de PII antes de encolarlo.

### Perfilador Asincrono
Background worker (`TraitExtractor`) que consume eventos de turno cerrado desde el EventBus. Usa el LLM para inferir características del usuario contra los `TraitAtom` candidatos y hace un upsert (SQL `UserTraits`). Opera fuera del tiempo de respuesta del usuario.

### Reflector Batch
Job offline (`ReflectorAtomGenerator`) disparado por cron. Lee el `ChatHistory` ya scrubbeado de SQL, detecta patrones que se repiten >= 5 veces, e infiere nuevos átomos (`domain` o `rule`). Escribe directamente en SLDB usando `sldb docs create` e inyecta el tag de estado `proposed`.


## Capas de Datos y Conocimiento
### Configuración del Negocio
Archivo `project.config.yaml`. Separa el código duro del dominio del negocio. Configura dinámicamente la identidad visible del bot (name, slug), la ruta al store SLDB (`kb_root`), el modelo LLM subyacente y el mapeo de los handlers de tools permitidos.

### SQL: Identidad y Estado
Capa de persistencia relacional transaccional (vía SQLAlchemy). Almacena los `Users`, la máquina de estados persistente (`SessionState`), el `ChatHistory` (ya scrubbeado de PII), los mapeos relacionales de `UserTraits`, y las tablas de negocio como Reservas.

### SLDB: Base de Conocimiento
Store de documentos semánticos. Hospeda los 10 modelos tipados del negocio, organizados en 4 familias (self, domain, conversation, user). Permite el intercambio de átomos para transformar o re-propocionar al agente conversacional.

### KGDB: Grafo de Flujo
Capa de base de datos de grafo en memoria (NetworkX persistido). Indexa las relaciones semánticas entre los nodos de `ConversationStep` (ej. `flows_to`, `grounded_by`), permitiendo al Ontologizador trazar la ruta de la conversación de forma programática.

