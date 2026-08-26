---
id: atom-clasificación-de-4-ramas-del-flujo-psp
title: Clasificación de 4 ramas del flujo PSP
five_wh_one_plus: what
tags:
- system:antonia
- domain:psp
- topic:clasificacion
provenance: null
---

# Clasificación de 4 ramas del flujo PSP

## Answer

El spec psp-flujo-atencion-chatbot.yml define sistema_clasifica como decisión con 4 ramas: (a) 'Intención Operativa F0' -> ejecuta_journey (responder con contenido preaprobado, sin generación libre); (b) 'Posible EA o FV' -> deriva_fv (genera ticket de farmacovigilancia, revisión humana <24h, registro con timestamp y texto textual del paciente); (c) 'Consulta Médica MedInfo' -> deriva_medinfo (genera ticket MedInfo, revisión humana; distinta de EA: es una pregunta clínica sin reporte de reacción); (d) 'Duda de Tratamiento F1' -> evalua_respuesta_ia (el LLM redacta y el Policy Gate aprueba o rechaza; si rechaza -> deriva_revision_general -> revisión humana). El runtime hoy clasifica solo en 3 (tool_call/fallback/nl) con heurística léxica; la KB de Antonia solo modela la rama EA (rule-antonia-eventos-adversos + step-antonia-evento-adverso). Faltan en KB: reglas clasificadoras para las otras 3 ramas, steps de MedInfo, revisión humana y journey operativo.
