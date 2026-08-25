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

- Implementar Router de Máquina de Estados [draft] - Construir State Router con debounce y manejo de tool-calling
- Alinear Agente Conversador a Nueva Arquitectura [draft] - Refactorizar conversador_apos para depender 100% del contexto
- Implementar Capa Relacional SQL [draft] - Definir SQLAlchemy/SQLModel para Users y UserTraits
- Implementar Perfilador Asincrono [draft] - Crear worker background que extrae traits y los guarda en SQL
- Implementar Reflector Batch [draft] - Job CRON que procesa historiales en batch a Domain/Rule atoms

## Task Details

_Generated from the task references above._

- Implementar Router de Máquina de Estados [draft] - Construir State Router con debounce y manejo de tool-calling
- Alinear Agente Conversador a Nueva Arquitectura [draft] - Refactorizar conversador_apos para depender 100% del contexto
- Implementar Capa Relacional SQL [draft] - Definir SQLAlchemy/SQLModel para Users y UserTraits
- Implementar Perfilador Asincrono [draft] - Crear worker background que extrae traits y los guarda en SQL
- Implementar Reflector Batch [draft] - Job CRON que procesa historiales en batch a Domain/Rule atoms
- Implementar Ontologizador Context Compiler [draft] - Motor determinista que resuelve p(Escenario, Pregunta, Perfil)
