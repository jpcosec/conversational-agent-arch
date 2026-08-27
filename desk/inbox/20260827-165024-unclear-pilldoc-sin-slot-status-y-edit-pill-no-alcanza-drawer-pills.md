---
kind: unclear
sender_project: gemini_test
created_at: 2026-08-27T16:50:24
status: open
---

# PillDoc sin slot status y edit pill no alcanza drawer/pills

PillDoc no tiene slot de status en su __template__: 'deskops edit pill <id> status active' reporta Updated pero no persiste nada en el archivo (los 3 pills de desk/contexts y los 2 del drawer siguen sin status). Ademas 'deskops edit pill' solo resuelve selectores en desk/contexts (no ve desk/drawer/pills), y 'sldb fields update docs/<pill>/status active' re-renderiza el pill del drawer por el template y pierde title (queda 'Context') y type; se restauraron los 2 archivos desde HEAD. Para el status explicito hace falta un slot en el template o una ruta CLI para pills del drawer.
