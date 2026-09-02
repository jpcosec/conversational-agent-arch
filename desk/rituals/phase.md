---
# ritual-xxx
id: ritual-phase
# List of step-xxx paths
steps:
- Identificar la siguiente capa de tareas cuyas dependencias ya estén resueltas y
  cuyos cambios no se pisen entre sí.
- 'Confirmar para cada tarea su bundle operativo: task doc, pills, atoms, archivos
  objetivo y validaciones.'
- Ejecutar cada tarea de la fase con su ritual de ejecución y cerrar cada una con
  su propia validación y commit atómico.
- Correr validación integrada de la fase cuando todas las tareas de la capa estén
  cerradas.
- Corregir regresiones de integración antes de abrir la siguiente capa.
- 'Reconciliar pills tocadas por la fase: retirar las obsoletas, fusionar duplicadas
  y promover residuo durable a atoms o materializaciones.'
- Capturar trabajo nuevo, dependencias descubiertas y pills de la siguiente fase antes
  de avanzar.
# e.g., layer:workflow, system:sldb
tags:
- workspace:desk
---

# Ritual de fase

## Purpose

_Explain why this ritual exists._

Cerrar una capa de trabajo como unidad de integración, no sólo como suma de tareas aisladas.

## Trigger

_State when this ritual should start._

Se ejecuta cuando el board tiene una capa lista de tareas activas que pueden avanzar sin solaparse.

## Preconditions

_List the conditions that must hold before running the ritual._

- Las dependencias entre tareas activas están explícitas.
- La capa lista está identificada y no comparte superficie operativa riesgosa.
- Cada tarea tiene contexto operativo y validación definidos.
- Existe una validación integrada de fase conocida de antemano.

## Validation

_List the checks that prove the ritual was performed correctly._

- Cada tarea de la fase pasó por ejecución, testing y closeout.
- Cada tarea cerró con su propia evidencia y su commit atómico.
- La validación integrada posterior al merge local pasó.
- Las pills tocadas por la fase quedaron reconciliadas.
- El trabajo descubierto para la siguiente fase quedó explicitado.

## Failure Modes

_List common mistakes this ritual prevents._

- Agrupar tareas relacionadas semánticamente aunque todavía dependan unas de otras.
- Saltar de cierres individuales a la siguiente fase sin validación integrada.
- Arrastrar pills obsoletas o duplicadas después de cerrar la fase.
- Esconder regresiones de interacción dentro de commits de tareas individuales.

## Completion

_Describe what completion looks like._

La capa actual quedó integrada, reconciliada y lista para dar paso a la siguiente.

## Step Details

_Generated from the step references above._
