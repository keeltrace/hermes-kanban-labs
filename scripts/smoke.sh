#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python -m compileall -q hermes_kanban_labs scripts
python -m pytest -q
PYTHONPATH="$ROOT" python -m hermes_kanban_labs.cli --help >/dev/null
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/upstream/hermes_cli"
cp tests/fixtures/current_main_snippets.txt "$TMP/upstream/hermes_cli/kanban_db.py"
PYTHONPATH="$ROOT" python -m hermes_kanban_labs.cli --config examples/workers.toml patch-upstream "$TMP/upstream" >/dev/null
python scripts/verify_upstream_contract.py "$TMP/upstream"
printf 'SMOKE PASS\n'
