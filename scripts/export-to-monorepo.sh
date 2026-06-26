#!/usr/bin/env bash
# scripts/export-to-monorepo.sh
#
# Export the current state of this web app into the course monorepo's P13 group
# folder. Development happens in THIS repo; run this whenever you want to refresh
# the monorepo snapshot, then commit on a `p13/*` branch in the monorepo and open
# a merge request.
#
# What it does:
#   1. Builds the Vue frontend (frontend/dist/).
#   2. rsyncs the backend package (backend/app/) into the monorepo P13 package.
#   3. Copies the built frontend into the package's static/ dir so FastAPI serves
#      it as a single process (uvicorn).
#
# It only touches source + static; it never edits the monorepo scaffolding
# (pyproject.toml, mprocs.yaml, root registration) — those are committed once.
#
# Usage:
#   ./scripts/export-to-monorepo.sh
#   MONOREPO=/path/to/monorepo ./scripts/export-to-monorepo.sh   # custom location

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONOREPO="${MONOREPO:-$REPO_ROOT/../monorepo}"
PKG="$MONOREPO/src/groups/p13_web_app_non_expert_users"
PKG_SRC="$PKG/src/p13_web_app_non_expert_users"

# --- sanity checks ---------------------------------------------------------
if [ ! -d "$MONOREPO" ]; then
  echo "ERROR: monorepo not found at '$MONOREPO'. Set MONOREPO=/path/to/monorepo." >&2
  exit 1
fi
if [ ! -f "$PKG/pyproject.toml" ]; then
  echo "ERROR: P13 scaffolding missing ($PKG/pyproject.toml)." >&2
  echo "       Create the group package scaffolding in the monorepo first." >&2
  exit 1
fi

# --- 1. build frontend -----------------------------------------------------
echo "==> Building frontend ..."
( cd "$REPO_ROOT/frontend" && npm install && npm run build )

# --- 2. sync backend source ------------------------------------------------
echo "==> Syncing backend source -> $PKG_SRC ..."
mkdir -p "$PKG_SRC"
rsync -a --delete \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='static/' \
  --exclude='data/' \
  --exclude='.env' \
  "$REPO_ROOT/backend/app/" "$PKG_SRC/"

# --- 3. copy built frontend into static/ -----------------------------------
echo "==> Copying built frontend -> $PKG_SRC/static ..."
rm -rf "$PKG_SRC/static"
mkdir -p "$PKG_SRC/static"
rsync -a "$REPO_ROOT/frontend/dist/" "$PKG_SRC/static/"

echo ""
echo "Export complete."
echo "Next steps (in the monorepo):"
echo "  cd \"$MONOREPO\""
echo "  git checkout -b p13/<short-description>"
echo "  git add src/groups/p13_web_app_non_expert_users"
echo "  git commit -m \"P13: update web app export\""
echo "  git push origin p13/<short-description>   # then open a merge request"
