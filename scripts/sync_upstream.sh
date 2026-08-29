#!/usr/bin/env bash
set -euo pipefail

# Run this FROM A FORK OF NousResearch/hermes-agent.
# It keeps the fork close to upstream main, then applies the tiny Labs seam.
# Stop on conflicts. Never force-push automatically.

UPSTREAM_REMOTE="${UPSTREAM_REMOTE:-upstream}"
UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/NousResearch/hermes-agent.git}"
LABS_DIR="${HERMES_KANBAN_LABS_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

if ! git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
  git remote add "$UPSTREAM_REMOTE" "$UPSTREAM_URL"
fi

git fetch "$UPSTREAM_REMOTE" main

git diff --quiet && git diff --cached --quiet || {
  echo "Refusing to sync: working tree is dirty" >&2
  exit 2
}

git rebase "$UPSTREAM_REMOTE/main"
python "$LABS_DIR/scripts/apply_upstream_patch.py" "$(pwd)"

echo
echo "Sync complete locally. Review:"
git status --short
git diff -- hermes_cli/kanban_db.py
echo
echo "Run targeted/full tests before committing or pushing."
