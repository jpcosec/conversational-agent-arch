# KB Agent Runtime

### Propuesta de Valor
Agente conversacional multi-dominio diseñado para operar en entornos de alta restricción. Su núcleo no depende de prompts hardcodeados, sino de la inyección dinámica de conocimiento estructurado (Átomos Semánticos), permitiendo cambiar de negocio (ej. de una clínica a una pizzería) simplemente cambiando la base de datos subyacente.

### Garantía Cero Alucinaciones
Regla arquitectónica estricta: el LLM tiene prohibido inventar información. Si el Ontologizador compila un contexto vacío (sin hechos ni reglas que sustenten la consulta del usuario), la máquina de estados fuerza una transición a un nodo de `BREAKPOINT_MISS`, obligando al agente a usar un mensaje de `fallback` determinista en lugar de alucinar una respuesta.

### Negocios Activos (KBs)
El sistema soporta múltiples negocios aislados. Actualmente conviven dos KBs principales: 'Antonia' (asistente clínico, producción) que vive en `knowledge/`, y 'Don Peppe' (pizzería, pruebas) que vive en `tests/knowledge/`. El archivo `project.config.yaml` actúa como el switch que define cuál está activo.


## Arquitectura y Componentes
> Ver [Documentación de Arquitectura](docs/ARCHITECTURE.md) y [Catálogo Visual](desk/spec2viz/build/architecture.html) para detalles técnicos.

## Glosario del Dominio
> Ver [Glosario de Conceptos](docs/GLOSSARY.md).

## Operaciones y Desarrollo
> Ver [Guía de Operaciones](docs/OPERATIONS.md).
