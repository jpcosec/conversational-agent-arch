---
id: tool-hcp-programar-recontacto
title: Tool — programar recontacto
atom_type: tool
tags:
- self:tools
- system:teva-hcp
provenance: null
summary: Tool para agendar un recontacto en la fecha y franja pedida por el médico,
  retomando la campaña donde quedó.
---

# Tool — programar recontacto

## Description

Agenda un recontacto con el médico en la fecha y franja que él pidió, retomando la campaña donde quedó.

## Parameters

```json
{"name": "programar_recontacto", "parameters": {"type": "object", "properties": {"hcp_id": {"type": "string", "description": "Identificador del médico"}, "fecha_recontacto": {"type": "string", "format": "date", "description": "Fecha solicitada por el médico"}, "franja_horaria": {"type": "string", "enum": ["manana", "tarde", "noche"], "description": "Franja preferida"}, "campania_id": {"type": "string", "description": "Campaña que se retomará"}, "nota_contexto": {"type": "string", "description": "Dónde quedó la conversación"}}, "required": ["hcp_id", "fecha_recontacto", "campania_id"]}}
```
