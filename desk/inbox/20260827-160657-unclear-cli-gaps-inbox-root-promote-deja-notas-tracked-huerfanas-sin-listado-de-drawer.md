---
kind: unclear
sender_project: gemini_test
created_at: 2026-08-27T16:06:57
status: open
---

# CLI gaps: inbox --root, promote deja notas tracked huerfanas, sin listado de drawer

CLI gaps observados al registrar tasks en el drawer: (1) 'deskops inbox' no acepta --root (usa --desk-root), a diferencia del resto de subcomandos y del skill. (2) 'deskops promote inbox-to-drawer-task' borra el archivo del inbox pero deja la nota tracked en el store: 'deskops status' la reporta como 'Invalid desk documents (missing)'; y el drawer task creado no queda tracked. (3) La plantilla de drawer task promovido pone un Goal generico ('Triage and resolve the inbox message...') y mete el contenido real en Scope; no hay forma de pasar goal/scope/validation separados. (4) No existe 'deskops list' para desk/drawer/tasks (list tasks solo muestra tasks activas) ni un flag drawer en 'add task'.
