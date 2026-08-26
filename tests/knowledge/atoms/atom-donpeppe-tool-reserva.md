---
id: crear_reserva
title: Tool crear reserva Don Peppe
atom_type: tool
tags:
- self:tools
- conversation:steps.booking
- system:donpeppe
provenance: null
---

# Tool crear reserva Don Peppe

## Description

Crea una reserva de mesa en Don Peppe. Llamar solo cuando se tienen confirmados fecha, hora y cantidad de personas, y la reserva cumple la regla de reservas (2 a 8 personas, no mismo día).

## Parameters

```json
{"name": "crear_reserva", "parameters": {"type": "object", "properties": {"fecha": {"type": "string"}, "hora": {"type": "string"}, "personas": {"type": "integer"}, "nombre": {"type": "string"}}, "required": ["fecha", "hora", "personas"]}}
```
