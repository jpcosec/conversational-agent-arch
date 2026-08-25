---
id: task-implementar-capa-sql
title: Implementar Capa Relacional SQL (Identidad y Sesión)
status: draft
---
## Objective
Reemplazar los diccionarios en memoria RAM por una base de datos relacional robusta que mantenga la identidad segregada de SLDB.

## Checklist
- [ ] Definir modelos en SQLAlchemy o SQLModel (`User`, `Session`, `UserTraitLink`).
- [ ] Implementar tabla de eventos CRON programados (`ScheduledEvent`).
- [ ] Integrar conectores SQL con el API Gateway asegurando que ningún dato PII llegue a la cadena cognitiva.