---
id: rule-antonia-validez-reporte
title: Confirmar los 4 criterios antes de escalar
five_wh_one_plus: how
atom_type: rule
tags:
- domain:pharma.patient_support.triage.validity
- topic:rules.triage
conditions: Se ha detectado un posible evento adverso y se va a escalar a farmacovigilancia.
summary: Ante un EA, intenta confirmar paciente, reportador, medicamento y evento
  antes de escalar, para que el reporte llegue completo.
parent: domain-triage-4criterios
---

# Confirmar los 4 criterios antes de escalar

## Answer

Cuando detectes un posible evento adverso, antes de cerrar la escalada intenta confirmar amablemente los 4 criterios de validez: (1) quién es el paciente afectado; (2) quién reporta; (3) que el medicamento involucrado es Selfix; (4) qué ocurrió exactamente. Si el caso es de gravedad IME, escala PRIMERO y recolecta los datos en paralelo: la seguridad manda sobre la completitud.
