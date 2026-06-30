#!/usr/bin/env bash
# scripts/export-to-monorepo.sh
#
# THE pipeline from this solo repo to the course monorepo.
#
#   edit here  ->  ./scripts/export-to-monorepo.sh [--push]  ->  monorepo p13 branch
#
# This repo is the single source of truth. The monorepo's P13 package is ALWAYS
# produced by this script — never hand-edit it over there, or the next export
# will overwrite the change. The script will only ever commit to our dedicated
# export branch (p13/initial-integration); it refuses to touch any other branch.
#
# What it does:
#   1. Builds the Vue frontend.
#   2. rsyncs the backend package (backend/app/) into the monorepo P13 package.
#   3. Copies the built frontend into the package's static/ dir (single-process
#      serving via uvicorn).
#   4. Commits the result on the export branch (unless --no-commit).
#   5. Pushes it (only with --push) — which updates the merge request.
#
# It only touches the P13 group folder; it never edits the monorepo scaffolding
# (root pyproject.toml, mprocs.yaml, uv.lock) — those are maintained separately.
#
# Usage:
#   ./scripts/export-to-monorepo.sh                 # build + sync + commit locally
#   ./scripts/export-to-monorepo.sh --push          # ... and push to GitLab
#   ./scripts/export-to-monorepo.sh --no-commit     # just sync files, no git
#   ./scripts/export-to-monorepo.sh -m "msg"        # custom commit message
#   MONOREPO=/path ./scripts/export-to-monorepo.sh  # custom monorepo location

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONOREPO="${MONOREPO:-$REPO_ROOT/../monorepo}"
EXPORT_BRANCH="${EXPORT_BRANCH:-p13/initial-integration}"
PKG="$MONOREPO/src/groups/p13_web_app_non_expert_users"
PKG_SRC="$PKG/src/p13_web_app_non_expert_users"

PUSH=false
COMMIT=true
MSG="P13: update web app export"

while [ $# -gt 0 ]; do
  case "$1" in
    --push) PUSH=true ;;
    --no-commit) COMMIT=false ;;
    -m) shift; MSG="${1:?-m needs a message}" ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
  shift
done

# --- sanity checks ---------------------------------------------------------
if [ ! -d "$MONOREPO" ]; then
  echo "ERROR: monorepo not found at '$MONOREPO'. Set MONOREPO=/path/to/monorepo." >&2
  exit 1
fi
if [ ! -f "$PKG/pyproject.toml" ]; then
  echo "ERROR: P13 scaffolding missing ($PKG/pyproject.toml)." >&2
  exit 1
fi

# Heads-up if the source tree has uncommitted work (the export reflects the
# working tree, not necessarily a committed state).
if [ -n "$(git -C "$REPO_ROOT" status --porcelain backend frontend 2>/dev/null)" ]; then
  echo "NOTE: backend/ or frontend/ has uncommitted changes — exporting the working tree."
fi

# --- 0. pin the monorepo to OUR export branch (only when committing) -------
if $COMMIT; then
  cur="$(git -C "$MONOREPO" branch --show-current)"
  if [ "$cur" != "$EXPORT_BRANCH" ]; then
    if [ -n "$(git -C "$MONOREPO" status --porcelain)" ]; then
      echo "ERROR: monorepo is on '$cur' with uncommitted changes." >&2
      echo "       Switch it to '$EXPORT_BRANCH' (or commit/stash) before exporting." >&2
      exit 1
    fi
    echo "==> Switching monorepo to '$EXPORT_BRANCH' ..."
    git -C "$MONOREPO" checkout "$EXPORT_BRANCH"
  fi
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

# Keep stray runtime artifacts out of the commit.
find "$PKG_SRC" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$PKG_SRC/data"

# --- 4. commit (+ push) on the export branch -------------------------------
if ! $COMMIT; then
  echo ""
  echo "Files synced (no commit). Review under: $PKG"
  exit 0
fi

git -C "$MONOREPO" add -A "src/groups/p13_web_app_non_expert_users"
if git -C "$MONOREPO" diff --cached --quiet; then
  echo ""
  echo "No changes to export — monorepo already matches this repo."
  exit 0
fi

git -C "$MONOREPO" commit -q -m "$MSG"
echo "==> Committed on $EXPORT_BRANCH: $(git -C "$MONOREPO" rev-parse --short HEAD)"

if $PUSH; then
  echo "==> Pushing $EXPORT_BRANCH ..."
  git -C "$MONOREPO" push origin "$EXPORT_BRANCH"
  echo "Pushed — the merge request is updated."
else
  echo "Not pushed. Run with --push (or: git -C \"$MONOREPO\" push origin $EXPORT_BRANCH)."
fi
