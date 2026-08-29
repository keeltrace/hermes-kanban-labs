from __future__ import annotations

import argparse
from pathlib import Path
import sys
import json

from .config import load_config, default_config_path
from .upstream_patch import apply_external_spawn_patch, UpstreamDriftError



def _upstream_kb():
    try:
        from hermes_cli import kanban_db as kb
    except ImportError as exc:
        raise RuntimeError("Hermes Agent must be installed in the same Python environment") from exc
    return kb


def _kb_connect(kb, board: str | None):
    try:
        return kb.connect(board=board)
    except TypeError:
        return kb.connect()


def _cmd_tree(args) -> int:
    from .tree import as_json, read_tree, render_vertical
    kb = _upstream_kb()
    conn = _kb_connect(kb, args.board)
    try:
        cards = read_tree(conn)
    finally:
        conn.close()
    print(as_json(cards) if args.json else render_vertical(cards))
    return 0


def _cmd_frontier(args) -> int:
    from .frontier import inspect_frontier
    from .inspection import resolve_scope_policy
    cfg = load_config(args.config)
    policy = resolve_scope_policy(cfg, board=args.board or "default", workflow=args.workflow, path=args.path)
    kb = _upstream_kb()
    conn = _kb_connect(kb, args.board)
    try:
        report = inspect_frontier(conn, policy)
    finally:
        conn.close()
    payload = {
        "board": args.board or "default",
        "workflow": args.workflow,
        "path": args.path,
        "open_cards": report.open_cards,
        "ready_cards": report.ready_cards,
        "max_open_cards": report.max_open_cards,
        "max_ready_cards": report.max_ready_cards,
        "max_children_per_card": policy.max_children_per_card,
        "max_depth": policy.max_depth,
        "saturated": report.saturated,
        "policy_sources": list(policy.sources),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        state = "SATURATED" if report.saturated else "OK"
        print(f"{state} board={payload['board']} open={report.open_cards}/{report.max_open_cards or '∞'} ready={report.ready_cards}/{report.max_ready_cards or '∞'}")
        if policy.max_children_per_card or policy.max_depth:
            print(f"limits children/card={policy.max_children_per_card or '∞'} depth={policy.max_depth or '∞'}")
        print("policy=" + " -> ".join(policy.sources))
    return 2 if report.saturated else 0

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

    tree = sub.add_parser("tree", help="Render the canonical Hermes board as a vertical workflow/path tree")
    tree.add_argument("--board")
    tree.add_argument("--json", action="store_true")
    tree.set_defaults(func=_cmd_tree)

    frontier = sub.add_parser("frontier", help="Inspect anti-sprawl frontier budgets against canonical Hermes state")
    frontier.add_argument("--board")
    frontier.add_argument("--workflow")
    frontier.add_argument("--path")
    frontier.add_argument("--json", action="store_true")
    frontier.set_defaults(func=_cmd_frontier)

    patch = sub.add_parser("patch-upstream", help="Apply/check the tiny external-spawn compatibility patch")
    patch.add_argument("hermes_repo")
    patch.add_argument("--check", action="store_true")
    patch.set_defaults(func=_cmd_patch)

    args = p.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
