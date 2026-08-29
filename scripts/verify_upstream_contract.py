#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys


def function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("hermes_repo")
    a = p.parse_args()
    path = Path(a.hermes_repo) / "hermes_cli" / "kanban_db.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    errors = []
    dispatch = function(tree, "dispatch_once")
    if dispatch is None or "spawn_fn" not in [x.arg for x in dispatch.args.kwonlyargs + dispatch.args.args]:
        errors.append("dispatch_once no longer exposes spawn_fn")
    if function(tree, "_default_spawn") is None:
        errors.append("_default_spawn is missing")
    heartbeat = function(tree, "heartbeat_claim")
    if heartbeat is None or "claimer" not in [x.arg for x in heartbeat.args.kwonlyargs + heartbeat.args.args]:
        errors.append("heartbeat_claim no longer supports claimer fencing")
    complete = function(tree, "complete_task")
    if complete is None or "expected_run_id" not in [x.arg for x in complete.args.kwonlyargs + complete.args.args]:
        errors.append("complete_task no longer supports expected_run_id fencing")
    if "if spawn_fn is None and profile_exists is not None" not in text:
        errors.append("Labs non-profile custom-spawn guard is not applied")
    if errors:
        for e in errors: print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("UPSTREAM CONTRACT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
