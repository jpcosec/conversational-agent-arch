---
# unclear | suggestion
kind: suggestion
# e.g., other_repo
sender_project: gemini_test
# e.g., target_repo
target_project: ⸢rev•target_project⸥
# ISO 8601 timestamp
created_at: '2026-09-08T17:40:00'
# open | closed
status: open
# project identity that acknowledged the note
acknowledged_by: ⸢rev•acknowledged_by⸥
# ISO 8601 timestamp, set when acknowledged
acknowledged_at: ⸢rev•acknowledged_at⸥
---

# Diagrama Antonia: sin salida desde registro_estado hacia enrolamiento/onboarding

_Describe the incoming message with enough evidence to triage._

Probado en REPL 2026-09-08. Si el orquestador pasa a registro_estado y la persona resulta ser nueva (no inscrita), no hay transicion a enrolamiento ni onboarding; el orquestador lo reporta como inconsistente y sigue preguntando como se siente. Falta transitions_to registro_estado -> enrolamiento (o volver a saludo).
