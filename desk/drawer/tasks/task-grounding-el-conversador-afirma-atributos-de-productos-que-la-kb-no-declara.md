# Grounding: el conversador afirma atributos de productos que la KB no declara

ID: task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-160609-suggestion-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara.md`.

## Scope

Goal: en donpeppe_perfil_vegetariano el bot afirmo que Margherita/Cuatro Quesos son vegetarianas sin que ningun atom lo diga (juez grounded reprueba; variable entre corridas). Es un gap generico de grounding (aplica a cualquier KB): el conversador infiere atributos no declarados.
Scope: prompt/contrato del conversador + gate (criterio grounded). Dato: la KB de ejemplo Don Peppe se va a recrear, asi que no arreglar el atom de pizzas — arreglar el mecanismo.
Validation: set -a; source .env; set +a; python -m pytest tests/e2e/simulation -m simulation -k perfil_vegetariano -q (2 corridas seguidas verdes)

## Source

- `desk/inbox/20260827-160609-suggestion-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara.md`

## Done When

- The message is resolved, answered, or promoted into active work.
