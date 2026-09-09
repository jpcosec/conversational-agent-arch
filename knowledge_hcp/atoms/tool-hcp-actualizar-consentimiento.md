---
id: tool-hcp-actualizar-consentimiento
title: Tool — actualizar consentimiento
atom_type: tool
tags:
- self:tools
- system:teva-hcp
provenance: null
summary: 'Tool para registrar la decisión de consentimiento del médico: baja de campaña,
  baja total o solicitud sobre sus datos.'
---

# Tool — actualizar consentimiento

## Description

Registra la decisión del médico sobre su consentimiento: baja de una campaña, baja total de comunicaciones, o solicitud sobre sus datos personales.

## Parameters

```json
{"name": "actualizar_consentimiento", "parameters": {"type": "object", "properties": {"hcp_id": {"type": "string", "description": "Identificador del médico"}, "nuevo_estado": {"type": "string", "enum": ["opt_in", "active_contact", "campaign_opt_out", "channel_opt_out", "dsr_erasure_requested"]}, "campania_id": {"type": "string", "description": "Requerido si la baja es de una campaña específica"}, "motivo_verbatim": {"type": "string", "description": "Cita textual de la solicitud del médico"}}, "required": ["hcp_id", "nuevo_estado", "motivo_verbatim"]}}
```
