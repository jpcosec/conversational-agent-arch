---
id: task-implementar-reflector-batch
title: Implementar Reflector (Consolidación Batch)
status: draft
---
## Objective
Construir un job periódico que analice logs históricos de conversaciones para engrosar la base de conocimiento SLDB de forma autónoma.

## Checklist
- [ ] Módulo de agregación de diálogos pasados sin PII.
- [ ] Pipeline LLM para identificar reglas implícitas o conocimiento funcional repetitivo.
- [ ] Generador de archivos markdown (`.md`) para formalizar los hallazgos como nuevos `RuleAtom` o `DomainAtom` en SLDB.