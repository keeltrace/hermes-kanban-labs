#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hermes_kanban_labs.upstream_patch import apply_external_spawn_patch, UpstreamDriftError


def main() -> int:
    p = argparse.ArgumentParser(description="Apply Hermes Kanban Labs' minimal current-main compatibility patch")
    p.add_argument("hermes_repo")
    p.add_argument("--check", action="store_true", help="detect whether the patch is needed without writing")
    a = p.parse_args()
    try:
        r = apply_external_spawn_patch(a.hermes_repo, write=not a.check)
    except (OSError, UpstreamDriftError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"path={r.path}")
    print(f"changed={r.changed}")
    print(f"before_sha256={r.before_sha256}")
    print(f"after_sha256={r.after_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
