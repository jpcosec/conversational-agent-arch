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

# Diagrama Antonia: despedida es terminal sin retorno

_Describe the incoming message with enough evidence to triage._

Probado en REPL 2026-09-08. Tras evento_adverso -> despedida, cualquier pedido posterior (agendar recordatorio, consulta) queda sin transicion (allowed = []) y termina en handoff generico. Falta un retorno (despedida -> saludo o registro_estado) o que saludo se reactive en la proxima conversacion.
