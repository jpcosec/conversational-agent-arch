---
id: registrar_enrolamiento
title: Tool registrar enrolamiento al programa
atom_type: tool
tags:
- self:tools
- conversation:steps.enrolamiento
- system:laboratorio-chile
provenance: null
summary: Marca a la persona como inscrita en el programa; requiere nombre, teléfono
  y correo confirmados.
---

# Tool registrar enrolamiento al programa

## Description

Registra el enrolamiento de la persona en el programa de acompañamiento. Llamar solo cuando se tienen confirmados su nombre, un teléfono de contacto y un correo electrónico.

## Parameters

```json
{"name": "registrar_enrolamiento", "parameters": {"type": "object", "properties": {"nombre": {"type": "string"}, "telefono": {"type": "string"}, "mail": {"type": "string"}}, "required": ["nombre", "telefono", "mail"]}}
```
