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
Regla clave: `is_empty=true` cuando `rules` Y `domain_facts` quedan ambos vacíos → el router transiciona a breakpoint_miss.

Ambigüedad resuelta — algoritmo de selección del subgrafo (determinista, sin embeddings en v1):
- `scenario` (str): etiqueta de dominio activa. Origen: para turno normal = `SessionState.active_domain` (campo str nullable; ver task-implementar-modelos-de-sesión-e-historial); para CRON = el campo `scenario` del payload del trigger sintético `{scenario: str, user_id: int}` (ver atom-trigger-sintetico-cron). Si `active_domain` es null (o el trigger no fija scenario), se usa el/los `domain:*` tags del store (KB_ROOT) por defecto.
- Selección: un Atom es relevante si sus tags de dominio hacen match con `scenario` (match exacto de tag `domain:<scenario>` o prefijo jerárquico, ej. scenario=pizza matchea domain:pizza y domain:pizza.horarios).
- `rules`/`domain_facts`: RuleAtoms y DomainAtoms cuyo tag de dominio matchea scenario.
- `tools`: ToolAtoms marcados como disponibles para ese scenario.
- `user_traits`: se leen tal cual desde UserTraits (SQL) por user_id, sin filtrar por scenario.
- Sin ranking semántico en v1: filtrado por match de tags, 100% determinista y testeable.

## Validation

- `pytest`: sembrar `.sldb_test/` de una pizzería + traits del user; afirmar que el payload contiene SOLO los ids del dominio pizza y ningún átomo irrelevante.
- Afirmar `is_empty=true` cuando se consulta un escenario sin átomos.
- Cero llamadas a LLM en todo el test.

## Done When

El payload cumple el contrato JSON, filtra exacto y marca is_empty correctamente.
