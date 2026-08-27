---
id: atom-modelo-de-ramas
title: Modelo de ramas
five_wh_one_plus: how
tags:
- layer:ops
- role:boundary
- topic:git-flow
provenance: README.md
---

# Modelo de ramas

## Answer

Cuatro tipos de rama (README.md, sección "Ramas, CI y releases"). `dev` es integración y la única rama donde se mergea — recibe `merge --no-ff` desde ramas de feature con la suite verde. `main` es estable — avanza sólo por fast-forward desde `dev` cuando pasa la suite completa, incluida la capa LLM. `production` es lo desplegado en Modal — la mueve únicamente `deploy/release.sh`, con tag `release-YYYYMMDD-<sha>`. Las features (`vitali`, `apoe`, …) viven como worktrees en `../_worktrees/<nombre>` — nacen de `dev`, se rebasean sobre `dev` mientras viven, vuelven con `--no-ff`, y al mergear se borran worktree y rama. Reglas — nada se commitea directo en `main` ni `production`; `main` nunca se mergea hacia `dev` (todo nace en `dev`); cero stashes (todo cambio probado se commitea); lo legacy se borra, no se archiva (el archivo es el historial de git). Ciclo completo de una feature — `git worktree add ../_worktrees/vitali -b vitali dev`; commits en el worktree; `git -C ../_worktrees/vitali rebase dev`; `git checkout dev && git merge --no-ff vitali`; `git worktree remove ../_worktrees/vitali && git branch -d vitali`; `git checkout main && git merge --ff-only dev`; `git push origin dev main`.
