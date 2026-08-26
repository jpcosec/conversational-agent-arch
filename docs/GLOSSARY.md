# Glosario de Conceptos

Definiciones de los términos ubicuos (Ubiquitous Language) utilizados en todo el ecosistema de KB Agent.

### Turno Extendido
El ciclo de vida completo de un mensaje de usuario. A diferencia de un request/response tradicional, el turno extendido incluye pausas en la ejecución síncrona para ejecutar herramientas externas (tools) y procesos asíncronos posteriores a la respuesta (como la extracción de perfiles y la reflexión en batch).

### Átomo Semántico (SLDB)
Unidad mínima de conocimiento y gobernanza. Técnicamente es un archivo Markdown con frontmatter YAML (formato SLDB). Todo en el sistema es un átomo: las reglas de negocio, los perfiles de usuario, los pasos del flujo, e incluso la propia documentación de arquitectura.

### Negocios Activos (KBs)
El sistema soporta múltiples negocios aislados. Actualmente conviven dos KBs principales: 'Antonia' (asistente clínico, producción) que vive en `knowledge/`, y 'Don Peppe' (pizzería, pruebas) que vive en `tests/knowledge/`. El archivo `project.config.yaml` actúa como el switch que define cuál está activo.

