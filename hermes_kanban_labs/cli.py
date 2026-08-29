from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import load_config, default_config_path
from .upstream_patch import apply_external_spawn_patch, UpstreamDriftError


def _cmd_doctor(args) -> int:
    from .executors.ssh_docker import doctor
    cfg = load_config(args.config)
    names = [args.worker] if args.worker else sorted(cfg.workers)
    rc = 0
    for name in names:
        worker = cfg.workers[name]
        ok, detail = doctor(worker, pull=args.pull)
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
        rc |= 0 if ok else 1
    return rc


def _cmd_patch(args) -> int:
    try:
        result = apply_external_spawn_patch(args.hermes_repo, write=not args.check)
    except UpstreamDriftError as exc:
        print(f"DRIFT: {exc}", file=sys.stderr)
        return 2
    mode = "would-change" if args.check and result.changed else ("changed" if result.changed else "already-applied/no-change")
    print(f"{mode}: {result.path}")
    print(f"before={result.before_sha256}")
    print(f"after={result.after_sha256}")
    return 0


def _cmd_dispatch(args) -> int:
    from .dispatcher import run
    run(args.config, args.board, args.interval, args.once)
    return 0


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="hkl",
        description="Experimental power-user execution backends for upstream Hermes Kanban",
    )
    p.add_argument("--config", default=str(default_config_path()))
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("dispatch", help="Run the canonical Hermes dispatcher with Labs spawn backends")
    d.add_argument("--board")
    d.add_argument("--interval", type=float, default=5.0)
    d.add_argument("--once", action="store_true")
    d.set_defaults(func=_cmd_dispatch)

    doc = sub.add_parser("doctor", help="Verify configured worker hosts and Docker")
    doc.add_argument("worker", nargs="?")
    doc.add_argument("--pull", action="store_true", help="also pull the configured Hermes image")
    doc.set_defaults(func=_cmd_doctor)

    patch = sub.add_parser("patch-upstream", help="Apply/check the tiny external-spawn compatibility patch")
    patch.add_argument("hermes_repo")
    patch.add_argument("--check", action="store_true")
    patch.set_defaults(func=_cmd_patch)

    args = p.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
