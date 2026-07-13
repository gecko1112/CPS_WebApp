#!/usr/bin/env bash
# scripts/export-to-monorepo.sh — sync OUR SOURCE into the monorepo's P13 group
# folder, on top of the latest main.
#
# ── The new monorepo world (Adrian/P10's restructure, 2026-07-09) ───────────
# P13 lives in the monorepo as a RAW SOURCE tree, not a built package:
#
#   src/groups/p13_web_app_non_expert_users/
#     backend/app/        <- ours (this repo's backend/app/)
#     backend/pyproject.toml  <- ADRIAN'S (uv workspace member, pinned deps)
#     frontend/src/       <- ours
#     frontend/public/    <- ours
#     frontend/index.html + vite/tailwind/postcss configs + package.json <- ours
#     frontend/bun.lock   <- ADRIAN'S (frontend deps installed with bun)
#     P13_*.md            <- course doc, not ours
#
# It runs via the monorepo's own scripts (never ours): scripts/run.sh starts
# p13_backend (uvicorn :8000) + p13_frontend (vite dev :5173, via bun);
# scripts/sync-code.sh rsyncs the monorepo to the Pi; install-packages.sh
# does uv sync + bun install. No frontend build, no static/ export anymore.
#
# ── What this script does ────────────────────────────────────────────────────
#   1. Fetches origin and re-creates branch p13/sync FROM origin/main —
#      so Adrian's latest work is the base and can never be overwritten.
#   2. rsyncs ONLY our source areas (listed above) into the group folder.
#      It never touches backend/pyproject.toml, bun.lock, or anything
#      outside src/groups/p13_web_app_non_expert_users/.
#   3. Commits; --push force-pushes the branch (safe: it's ours alone,
#      always freshly cut from main) for a merge request.
#
# The old flow (built frontend + static/ package on p13/initial-integration)
# is dead — that branch is abandoned history, do not touch it.
#
# Usage:
#   ./scripts/export-to-monorepo.sh                 # sync + commit locally
#   ./scripts/export-to-monorepo.sh --push          # ... and push for an MR
#   ./scripts/export-to-monorepo.sh --no-commit     # just sync, no git
#   ./scripts/export-to-monorepo.sh -m "msg"        # custom commit message
#   MONOREPO=/path ./scripts/export-to-monorepo.sh  # custom monorepo location

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONOREPO="${MONOREPO:-$REPO_ROOT/../monorepo}"
SYNC_BRANCH="${SYNC_BRANCH:-p13/sync}"
PKG="$MONOREPO/src/groups/p13_web_app_non_expert_users"

PUSH=false
COMMIT=true
MSG="P13: sync web app source from group repo"

while [ $# -gt 0 ]; do
  case "$1" in
    --push) PUSH=true ;;
    --no-commit) COMMIT=false ;;
    -m) shift; MSG="${1:?-m needs a message}" ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
  shift
done

# --- sanity checks -----------------------------------------------------------
[ -d "$MONOREPO" ] || { echo "ERROR: monorepo not found at '$MONOREPO'." >&2; exit 1; }
if [ -n "$(git -C "$REPO_ROOT" status --porcelain backend frontend 2>/dev/null)" ]; then
  echo "NOTE: backend/ or frontend/ has uncommitted changes — exporting the working tree."
fi

# --- 1. base the sync branch on the LATEST main ------------------------------
if $COMMIT; then
  if [ -n "$(git -C "$MONOREPO" status --porcelain)" ]; then
    echo "ERROR: monorepo has uncommitted changes — commit/stash them first." >&2
    exit 1
  fi
  echo "==> Fetching origin and cutting $SYNC_BRANCH from origin/main ..."
  git -C "$MONOREPO" fetch origin
  git -C "$MONOREPO" checkout -B "$SYNC_BRANCH" origin/main
fi

# The layout check runs AFTER the checkout so it validates what we sync into.
[ -d "$PKG/backend/app" ] || {
  echo "ERROR: expected Adrian's layout ($PKG/backend/app) — monorepo too old?" >&2
  exit 1
}

# --- 2. sync our source areas (and nothing else) ------------------------------
echo "==> Syncing backend/app ..."
rsync -a --delete \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='data/' --exclude='.env' \
  "$REPO_ROOT/backend/app/" "$PKG/backend/app/"

echo "==> Syncing frontend src/, public/ + root config files ..."
rsync -a --delete "$REPO_ROOT/frontend/src/"    "$PKG/frontend/src/"
rsync -a --delete "$REPO_ROOT/frontend/public/" "$PKG/frontend/public/"
for f in index.html vite.config.js tailwind.config.js postcss.config.js \
         package.json package-lock.json; do
  [ -f "$REPO_ROOT/frontend/$f" ] && cp "$REPO_ROOT/frontend/$f" "$PKG/frontend/$f"
done

# Deliberately untouched: backend/pyproject.toml, frontend/bun.lock (Adrian's).
if git -C "$MONOREPO" status --porcelain | grep -q "frontend/package.json"; then
  echo "NOTE: package.json changed — run 'bun install' in the group frontend and"
  echo "      commit the updated bun.lock (coordinate with Adrian)."
fi

# --- 3. commit (+ push) --------------------------------------------------------
if ! $COMMIT; then
  echo ""
  echo "Files synced (no commit). Review under: $PKG"
  exit 0
fi

git -C "$MONOREPO" add -A "src/groups/p13_web_app_non_expert_users"
if git -C "$MONOREPO" diff --cached --quiet; then
  echo ""
  echo "No changes to export — monorepo main already matches this repo."
  exit 0
fi

git -C "$MONOREPO" commit -q -m "$MSG"
echo "==> Committed on $SYNC_BRANCH (base: origin/main): $(git -C "$MONOREPO" rev-parse --short HEAD)"

if $PUSH; then
  echo "==> Pushing $SYNC_BRANCH ..."
  git -C "$MONOREPO" push --force-with-lease origin "$SYNC_BRANCH"
  echo "Pushed — open/refresh the MR from $SYNC_BRANCH to main (merge is P10/Adrian's call)."
else
  echo "Not pushed. Run with --push (or: git -C \"$MONOREPO\" push --force-with-lease origin $SYNC_BRANCH)."
fi
