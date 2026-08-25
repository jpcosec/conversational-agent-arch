---
id: task-implementar-perfilador-async
title: Implementar Perfilador Asíncrono
status: draft
---
## Objective
Desarrollar el agente de background (Perfilador) que escuche los turnos de conversación para extraer características (`traits`) del usuario sin afectar la latencia del chat.

## Checklist
- [ ] Crear el worker/cola asíncrona conectada al Router.
- [ ] Prompt/Lógica para extraer rasgos explícitos de un turno conversacional.
- [ ] Búsqueda semántica en SLDB para asociar el rasgo detectado con un `TraitAtom` existente.
- [ ] Lógica para insertar la relación N:M en la tabla SQL `UserTraits`.