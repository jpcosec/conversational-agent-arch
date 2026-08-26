---
id: pill-maquina-de-estados-pausa-en-tool-calling
title: La Máquina de Estados pausa durante el Tool Calling
type: pill
tags:
  - rule:state-machine
---
# Context

- **Pausa Explícita**: La ejecución de una API externa (ej. Calendar, CRM) no ocurre "en vuelo" dentro de un solo prompt. La Máquina de Estados debe transicionar explícitamente a un estado de pausa (`waiting_tool`).
- **Resolución**: Mientras el orquestador ejecuta el comando del Conversador, el flujo de atención al usuario queda en espera.
- **Reingreso**: El JSON devuelto por la herramienta se reinyecta al contexto como un "Turno de Sistema" antes de reactivar al Conversador para que redacte la respuesta final.