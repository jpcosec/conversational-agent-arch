---
id: task-implementar-compilador-de-contexto
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-compilador-de-contexto
current_node: checklist-task-implementar-compilador-de-contexto-execution-ready
history: []
references: []
depends_on:
- task-implementar-conector-sldb-del-ontologizador
- task-implementar-modelos-de-identidad-sql
pills: []
files: []
checklists:
- checklist-task-implementar-compilador-de-contexto-execution-ready
- checklist-task-implementar-compilador-de-contexto-testing-ready
- checklist-task-implementar-compilador-de-contexto-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-contexto-compilado
---

# Implementar Compilador de Contexto

## Rationale

Resuelve la ecuación Contexto = p(Escenario, Pregunta, Perfil) de forma determinista. Es el corazón del diseño anti-alucinación.

## Goal

_Describe the concrete result this task must produce._

Filtrar el subgrafo exacto y generar el payload JSON.

## Scope

EN: Filtrado del subgrafo relevante y ensamblado del payload "Contexto Compilado".
FUERA: lectura cruda de SLDB (conector) y generación NL (Conversador).

## Implementation Path

`kb_agent/ontologizador/compiler.py`

Ambigüedad resuelta — contrato del payload "Contexto Compilado" (JSON):
```
{
  "scenario": str,
  "question": str,
  "user_traits": [str],        // trait_ids desde SQL (UserTraits)
  "rules": [{id, body}],       // RuleAtoms aplicables
  "domain_facts": [{id, body}],// DomainAtoms del escenario
  "tools": [json_schema],      // ToolAtoms -> function_declarations
  "is_empty": bool             // true si no hay ni rules ni domain_facts
}
```
Regla clave: `is_empty=true` cuando el subgrafo no aporta conocimiento → el Conversador debe caer en fallback.

## Validation

- `pytest`: sembrar `.sldb_test/` de una pizzería + traits del user; afirmar que el payload contiene SOLO los ids del dominio pizza y ningún átomo irrelevante.
- Afirmar `is_empty=true` cuando se consulta un escenario sin átomos.
- Cero llamadas a LLM en todo el test.

## Done When

El payload cumple el contrato JSON, filtra exacto y marca is_empty correctamente.
