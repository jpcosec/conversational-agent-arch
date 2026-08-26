---
id: agendar_recordatorio
title: Tool agendar recordatorio de aplicación
atom_type: tool
tags:
- self:tools
- conversation:steps.agendar_recordatorio
- system:laboratorio-chile
provenance: null
---

# Tool agendar recordatorio de aplicación

## Description

Agenda un recordatorio semanal de aplicación de Selfix para la persona. Llamar solo cuando se tienen confirmados el día y la hora del recordatorio.

## Parameters

```json
{"name": "agendar_recordatorio", "parameters": {"type": "object", "properties": {"dia": {"type": "string"}, "hora": {"type": "string"}, "nombre": {"type": "string"}}, "required": ["dia", "hora"]}}
```
