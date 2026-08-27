# Mindmap: no hay escritura de atoms desde la UI

ID: task-mindmap-no-hay-escritura-de-atoms-desde-la-ui
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184453-suggestion-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md`.

## Scope

Goal: decidir si la KB se edita desde la UI o se queda read-only, y ejecutar esa decision.
Scope: la vista quedo explicitamente read-only (ver el commit que saco el state muerto y el hint 'doble-click edita'), pero la pregunta de fondo sigue abierta. Hoy no existe capa de escritura de atoms: kb_agent solo tiene readers (ontologizador/sldb_reader.py:28, ontologizador/kgdb_reader.py:83), no hay endpoint (PUT/PATCH/POST sobre /api/atom/{id} devuelven 405) y el store .sldb se consume por load_runtime_documents, de solo lectura. Consecuencia lateral ya visible: las acciones del toolbar del mindmap que mutan el grafo (borrar, +hijo, +hermano, link horizontal) viven solo en el cliente y se pierden al recargar -- prometen persistencia que no existe, igual que el hint que se saco. Implementarlo son ~2-3 dias (modal de edicion + PATCH /api/atom/{id} + capa de escritura: averiguar si sldb expone API de escritura o escribir el YAML fuente y re-indexar el store). Es decision de arquitectura, no solo de codigo: el pipeline del repo es spec->atoms via CLI (deskops/spec2viz), asi que editar atoms en caliente desde la UI puede ir a contrapelo de ese diseno. La alternativa barata es asumir read-only y sacar tambien las acciones locales del toolbar.
Validation: si se implementa, tests en tests/ui/test_mindmap.py para editar->guardar->recargar->persiste, y actualizar frontends/UI-GUIDE.md; si se descarta, sacar las mutaciones locales del toolbar y documentarlo.

## Source

- `desk/inbox/20260827-184453-suggestion-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md`

## Done When

- The message is resolved, answered, or promoted into active work.
