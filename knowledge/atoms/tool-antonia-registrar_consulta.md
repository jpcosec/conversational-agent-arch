---
id: registrar_consulta
title: Tool registrar consulta MedInfo / evento adverso
atom_type: tool
tags:
- self:tools
- conversation:steps.derivacion_medinfo
- conversation:steps.evento_adverso
- system:laboratorio-chile
provenance: null
summary: Registra un ticket MedInfo (consulta medica) o un reporte de evento adverso
  para farmacovigilancia con el texto textual de la persona.
---

# Tool registrar consulta MedInfo / evento adverso

## Description

Registra la consulta medica (tipo medinfo) o el evento adverso (tipo evento_adverso) que la persona reporto, con su texto textual, para que un profesional del programa la atienda. Llamar apenas la persona formulo la consulta o describio el malestar; no prometer que se registro sin llamarla.

## Parameters

```json
{"name": "registrar_consulta", "parameters": {"type": "object", "properties": {"tipo": {"type": "string", "enum": ["medinfo", "evento_adverso"], "description": "medinfo: consulta medica del programa. evento_adverso: malestar, sintoma o reaccion para farmacovigilancia."}, "texto": {"type": "string", "description": "Lo que dijo la persona, textual, sin interpretar."}, "urgente": {"type": "boolean", "description": "true solo si la persona dice que es urgente o describe algo grave."}}, "required": ["tipo", "texto"]}}
```
