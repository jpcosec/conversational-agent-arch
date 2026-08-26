#!/usr/bin/env bash
# Micro CI/CD: gate -> deploy -> tag -> track.
#
# Deja registrada en la rama `production` (marcada + taggeada) EXACTAMENTE la
# version que quedo desplegada en Modal. No hay magia: corre la suite offline,
# despliega, y solo si todo pasa avanza `production` y crea el tag.
#
# Por que local y no GitHub Actions: kgdb no tiene remoto publicable, asi que
# un runner limpio de GitHub no puede `pip install` las deps. Este script corre
# donde SI estan las deps (tu entorno) y es la fuente de verdad de "que hay
# arriba". Ver deploy/README.md.
#
# Uso:
#   deploy/release.sh                 # tag automatico vN por fecha+sha
#   deploy/release.sh v0.3.0          # tag explicito
#   SKIP_DEPLOY=1 deploy/release.sh   # solo gate + tag (no toca Modal)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PROD_BRANCH="production"
TAG="${1:-release-$(date +%Y%m%d)-$(git rev-parse --short HEAD)}"

echo "==> Preflight"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree sucio. Commitea o stashea antes de release." >&2
  git status --short >&2
  exit 1
fi
SRC_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
SHA="$(git rev-parse HEAD)"
echo "    rama=$SRC_BRANCH sha=${SHA:0:12} tag=$TAG"

echo "==> Gate: suite offline (unit + integration, sin LLM)"
SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q

if [[ "${SKIP_DEPLOY:-0}" != "1" ]]; then
  echo "==> Deploy a Modal"
  modal deploy deploy/modal_app.py
else
  echo "==> SKIP_DEPLOY=1: no se despliega"
fi

echo "==> Marcar version desplegada en '$PROD_BRANCH' + tag '$TAG'"
git tag -f -a "$TAG" -m "release: $SRC_BRANCH @ ${SHA:0:12} (deploy $(date -u +%FT%TZ))"
git branch -f "$PROD_BRANCH" "$SHA"

echo "==> Listo"
echo "    production -> ${SHA:0:12}"
echo "    tag        -> $TAG"
echo "    push:  git push origin $PROD_BRANCH && git push origin $TAG"
