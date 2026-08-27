---
kind: unclear
sender_project: gemini_test
created_at: 2026-08-27T16:48:46
status: open
---

# edit/extractor corre secciones vacias y advance --to no toca status

deskops edit re-lee el doc con el extractor de sldb y, si una seccion del template esta vacia (goal/scope/implementation_path/validation), el extractor corre el contenido de la seccion siguiente hacia la vacia; cada edit sucesivo corrompe campos vecinos (paso con task-ui-foundations y task-recomponer, que ademas fallaban 'Idempotency fail' en sldb docs track). Ademas deskops advance task --to complete deja current_node=complete pero status sin cambiar; hubo que usar deskops edit task <id> status complete.
