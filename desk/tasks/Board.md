---
# board-xxx
id: board-001
# Affected workspace or domain
scope: desk
# List of task-xxx paths
tasks:
- desk/tasks/task-implementar-router-de-máquina-de-estados.md
- desk/tasks/task-alinear-agente-conversador-a-nueva-arquitectura.md
- desk/tasks/task-implementar-capa-relacional-sql.md
- desk/tasks/task-implementar-perfilador-asincrono.md
- desk/tasks/task-implementar-reflector-batch.md
- desk/tasks/task-implementar-ontologizador-context-compiler.md
- desk/tasks/task-implementar-core-state-machine-del-router.md
- desk/tasks/task-implementar-debounce-buffer-en-router.md
- desk/tasks/task-implementar-pausa-de-tools-en-router.md
- desk/tasks/task-implementar-modelos-de-identidad-sql.md
- desk/tasks/task-implementar-modelos-de-sesión-e-historial.md
- desk/tasks/task-implementar-scrubber-de-pii.md
- desk/tasks/task-implementar-conector-sldb-del-ontologizador.md
- desk/tasks/task-implementar-compilador-de-contexto.md
- desk/tasks/task-implementar-fallback-estricto-del-conversador.md
- desk/tasks/task-implementar-tool-calling-estructurado.md
- desk/tasks/task-implementar-listener-asíncrono-del-perfilador.md
- desk/tasks/task-implementar-extractor-de-traits.md
- desk/tasks/task-implementar-batch-reader-del-reflector.md
- desk/tasks/task-implementar-generador-de-átomos-sldb.md
# List of pill-xxx paths
pills:
- desk/contexts/pills.md
# List of ritual-xxx paths
rituals:
- desk/rituals/execution.md
- desk/rituals/testing.md
- desk/rituals/closeout.md
# e.g., system:sldb, workspace:desk
tags:
- workspace:desk
---

# gemini_test Board

## Purpose

_Explain what this board routes and why it exists._



## Notes

_Add short operational notes about the current routed set._

- Implementar Core State Machine del Router [draft] - Conectar las transiciones básicas idle -> eval -> draft -> idle.
- Implementar Debounce Buffer en Router [draft] - Retener mensajes por 1s para agrupar ráfagas antes de transicionar.
- Implementar Pausa de Tools en Router [draft] - Pausar la SM en waiting_tool y reanudar con System Turn.
- Implementar Modelos de Identidad SQL [draft] - Tablas Users y UserTraits en SQLAlchemy.
- Implementar Modelos de Sesión e Historial [draft] - Tablas SessionState y ChatHistory.
- Implementar Scrubber de PII [draft] - Filtro que limpia ChatHistory antes de exponerlo a otros motores.
- Implementar Conector SLDB del Ontologizador [draft] - Leer de forma segura rules, tools y domains desde SLDB.
- Implementar Compilador de Contexto [draft] - Filtrar el subgrafo exacto y generar el payload JSON.
- Implementar Fallback Estricto del Conversador [draft] - Forzar salida 'No sé' si el contexto es vacío (cero alucinación).
- Implementar Tool Calling Estructurado [draft] - Emitir function_call JSON en lugar de texto si hay ToolAtoms.
- Implementar Listener Asíncrono del Perfilador [draft] - Conectar un worker que consuma eventos de turnos en background.
- Implementar Extractor de Traits [draft] - Analizar texto y mapear a TraitAtoms en la tabla SQL.
- Implementar Batch Reader del Reflector [draft] - Leer lotes históricos limpios desde SQL.

## Task Details

_Generated from the task references above._

- Implementar Core State Machine del Router [draft] - Conectar las transiciones básicas idle -> eval -> draft -> idle.
- Implementar Debounce Buffer en Router [draft] - Retener mensajes por 1s para agrupar ráfagas antes de transicionar.
- Implementar Pausa de Tools en Router [draft] - Pausar la SM en waiting_tool y reanudar con System Turn.
- Implementar Modelos de Identidad SQL [draft] - Tablas Users y UserTraits en SQLAlchemy.
- Implementar Modelos de Sesión e Historial [draft] - Tablas SessionState y ChatHistory.
- Implementar Scrubber de PII [draft] - Filtro que limpia ChatHistory antes de exponerlo a otros motores.
- Implementar Conector SLDB del Ontologizador [draft] - Leer de forma segura rules, tools y domains desde SLDB.
- Implementar Compilador de Contexto [draft] - Filtrar el subgrafo exacto y generar el payload JSON.
- Implementar Fallback Estricto del Conversador [draft] - Forzar salida 'No sé' si el contexto es vacío (cero alucinación).
- Implementar Tool Calling Estructurado [draft] - Emitir function_call JSON en lugar de texto si hay ToolAtoms.
- Implementar Listener Asíncrono del Perfilador [draft] - Conectar un worker que consuma eventos de turnos en background.
- Implementar Extractor de Traits [draft] - Analizar texto y mapear a TraitAtoms en la tabla SQL.
- Implementar Batch Reader del Reflector [draft] - Leer lotes históricos limpios desde SQL.
- Implementar Generador de Átomos SLDB [draft] - Convertir patrones históricos en archivos físicos .md.
