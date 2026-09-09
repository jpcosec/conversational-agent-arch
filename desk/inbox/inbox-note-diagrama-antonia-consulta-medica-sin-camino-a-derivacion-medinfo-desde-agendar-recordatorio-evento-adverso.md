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
status: closed
# project identity that acknowledged the note
acknowledged_by: ⸢rev•acknowledged_by⸥
# ISO 8601 timestamp, set when acknowledged
acknowledged_at: ⸢rev•acknowledged_at⸥
---

# Diagrama Antonia: consulta medica sin camino a derivacion_medinfo desde agendar_recordatorio/evento_adverso

_Describe the incoming message with enough evidence to triage._

Probado en REPL 2026-09-08. Una pregunta de dosis o de dosis olvidada hecha en agendar_recordatorio o evento_adverso no puede ir a derivacion_medinfo (solo recompra / despedida): el conversador deriva al medico en texto pero no queda ticket MedInfo. Faltan aristas transitions_to hacia derivacion_medinfo desde esos steps.
