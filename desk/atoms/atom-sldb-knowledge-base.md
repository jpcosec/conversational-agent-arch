---
id: atom-sldb-knowledge-base
title: 'SLDB: Base de Conocimiento'
five_wh_one_plus: what
tags:
- layer:knowledge
- role:data
provenance: architecture-audit
---

# SLDB: Base de Conocimiento

## Answer

Store de documentos semánticos. Hospeda los 10 modelos tipados del negocio, organizados en 4 familias (self, domain, conversation, user). Permite el intercambio de átomos para transformar o re-proponer al agente conversacional. Cuenta con una guarda contra el defecto invisible: `KnowledgeOperations.audit_embeddings` cuenta los atoms sin vector separando los que faltan de los que no llevan por diseño (`AgentFraming`, que se carga por rol y no se recupera por similitud) y devuelve `ok=False` si hay atoms que deberían tener embedding y no lo tienen. Sin esa auditoría una KB entera sin vectores sigue respondiendo por fuzzy literal y nada falla desde afuera (pasó con una KB al 50% sin embedding); el chequeo está expuesto en el CLI (`kb index audit`) para arranque o CI.
