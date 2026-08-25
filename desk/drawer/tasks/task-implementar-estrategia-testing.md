---
id: task-implementar-estrategia-testing
title: Implementar Estrategia de Testing (4 Niveles)
status: draft
---
## Objective
Construir la suite de pruebas multi-nivel para asegurar la fiabilidad del agente sin tests quebradizos, aislando el determinismo de la generación.

## Checklist
- [ ] Nivel 1: Tests unitarios de la máquina de estados y debounce en PyTest.
- [ ] Nivel 2: Tests LLM-as-a-judge para asegurar que el Conversador obedece el punto de quiebre (Fallback estricto).
- [ ] Nivel 3: Simulador End-to-End con un subgrafo dummy en SLDB (`atom-test-pizzeria`).
- [ ] Nivel 4: Script de Shadow Mode usando Golden Transcripts en la infraestructura deskops.