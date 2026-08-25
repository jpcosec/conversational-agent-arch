---
id: task-implementar-router-de-estado
title: Implementar Router de Máquina de Estados de la Conversación
status: draft
---
## Objective
Construir la clase en Python que orqueste la Máquina de Estados definida en `state.conversation-flow.yml`, reemplazando el ruteo lineal de FastAPI.

## Checklist
- [ ] Implementar ventana de `buffering` (debounce temporal) para agrupar multi-mensajes.
- [ ] Conectar el enrutamiento base (idle -> buffering -> evaluating_context).
- [ ] Implementar la pausa arquitectónica `waiting_tool` para delegación externa.
- [ ] Manejar la inyección sintética del CRON (proactividad).