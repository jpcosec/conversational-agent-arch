---
id: crear_reserva
title: Tool crear reserva Don Peppe
five_wh_one_plus: what
tags:
- atom_type:tool
- self:tools
- conversation:steps.booking
- source:e2e
provenance: null
---

# Tool crear reserva Don Peppe

## Answer

Crea una reserva de mesa. Schema JSON:
```json
{"name": "crear_reserva", "parameters": {"type": "object", "properties": {"fecha": {"type": "string"}, "hora": {"type": "string"}, "personas": {"type": "integer"}, "nombre": {"type": "string"}}, "required": ["fecha", "hora", "personas"]}}
```