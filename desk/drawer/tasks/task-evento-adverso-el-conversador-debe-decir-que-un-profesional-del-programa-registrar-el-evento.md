# Evento adverso: el conversador debe decir que un profesional del programa registrará el evento

ID: task-evento-adverso-el-conversador-debe-decir-que-un-profesional-del-programa-registrar-el-evento
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-160608-suggestion-evento-adverso-el-conversador-debe-decir-que-un-profesional-del-programa-registrar-el-evento.md`.

## Scope

Goal: cumplir rule-antonia-eventos-adversos en el escenario antonia_evento_adverso (tests/e2e/simulation/scenarios.py). Hoy el bot deriva al medico tratante pero omite decir que un profesional del programa registrara el evento; el juez LLM reprueba adverse_event_handling.
Scope: KB knowledge/ (rule atom + step del flujo) y/o prompt del conversador; no tocar la policy determinista.
Validation: set -a; source .env; set +a; python -m pytest tests/e2e/simulation -m simulation -k antonia_evento_adverso -q

## Source

- `desk/inbox/20260827-160608-suggestion-evento-adverso-el-conversador-debe-decir-que-un-profesional-del-programa-registrar-el-evento.md`

## Done When

- The message is resolved, answered, or promoted into active work.
