---
# unclear | suggestion
kind: suggestion
# e.g., other_repo
sender_project: gemini_test
# e.g., target_repo
target_project: ⸢rev•target_project⸥
# ISO 8601 timestamp
created_at: '2026-09-08T22:10:00'
# open | closed
status: closed
# project identity that acknowledged the note
acknowledged_by: ⸢rev•acknowledged_by⸥
# ISO 8601 timestamp, set when acknowledged
acknowledged_at: ⸢rev•acknowledged_at⸥
---

# Datos que la persona dice (medico, dia de aplicacion, nombre) no se persisten como slots

_Describe the incoming message with enough evidence to triage._

REPL 2026-09-08: Pedro dijo en el turno 1 'mi medico es la doctora Soto y me aplico los jueves'. Diez turnos despues, '¿como se llama mi medico?' cayo al fallback y '¿que dia me toca?' respondio 'lo ves con tu medico'. Solo se persisten email/telefono/preferencia (lead_slots). Los required_slots de cada step (nombre, dia de aplicacion, semana) deberian capturarse a flow_slots y volver al prompt en cada turno, no depender de la ventana de historial.
