from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .config import load_config
from .context import build_task_context
from .frontier import inspect_frontier
from .policy import resolve_execution_policy


def _connect(kb, board: str | None):
    try:
        return kb.connect(board=board)
    except TypeError:
        if board:
            os.environ["HERMES_KANBAN_BOARD"] = board
        return kb.connect()


def make_spawn(config_path: str, *, kb):
    cfg = load_config(config_path)

    def spawn(task, workspace: str, *, board: str | None = None):
        assignee = getattr(task, "assignee", None)
        if not assignee or assignee not in cfg.workers:
            # Mixed mode: ordinary Hermes profiles keep using the exact upstream path.
            return kb._default_spawn(task, workspace, board=board)

        worker = cfg.workers[assignee]
        policy = resolve_execution_policy(cfg, worker, task, board)

        # Build the remote snapshot from the same canonical board that owns the claim.
        conn = _connect(kb, board)
        try:
            frontier = inspect_frontier(conn, policy)
            prompt = build_task_context(conn, task, policy=policy, frontier=frontier)
        finally:
            conn.close()

        payload = {
            "task_id": task.id,
            "worker": assignee,
            "board": board,
            "workspace": workspace,
            "workspace_kind": getattr(task, "workspace_kind", None),
            "branch_name": getattr(task, "branch_name", None),
            "workflow_template_id": getattr(task, "workflow_template_id", None),
            "current_step_key": getattr(task, "current_step_key", None),
            "run_id": getattr(task, "current_run_id", None),
            "claim_lock": getattr(task, "claim_lock", None),
            "prompt": prompt,
            "execution": {
                "model": policy.model,
                "provider": policy.provider,
                "reasoning_effort": policy.reasoning_effort,
                "skills": list(policy.skills),
                "policy_sources": list(policy.sources),
            },
            "frontier": {
                "open_cards": frontier.open_cards,
                "ready_cards": frontier.ready_cards,
                "max_open_cards": frontier.max_open_cards,
                "max_ready_cards": frontier.max_ready_cards,
                "saturated": frontier.saturated,
            },
            "config": str(Path(config_path).expanduser().resolve()),
        }
        state = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "kanban-labs" / "runs"
        state.mkdir(parents=True, exist_ok=True)
        fd, payload_path = tempfile.mkstemp(prefix=f"{task.id}-", suffix=".json", dir=state)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        try:
            os.chmod(payload_path, 0o600)
        except OSError:
            pass

        log_dir = kb.worker_logs_dir(board=board)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_f = open(log_dir / f"{task.id}.labs.log", "ab", buffering=0)
        cmd = [sys.executable, "-m", "hermes_kanban_labs.bridge", payload_path]
        proc = subprocess.Popen(
            cmd,
            cwd=workspace if workspace and os.path.isdir(workspace) else None,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return proc.pid

    return spawn


def dispatch_once(config_path: str, board: str | None = None):
    try:
        from hermes_cli import kanban_db as kb
    except ImportError as exc:
        raise RuntimeError("Hermes Agent must be installed in the same Python environment") from exc
    if board:
        os.environ["HERMES_KANBAN_BOARD"] = board
    kb.init_db(board=board) if board else kb.init_db()
    conn = _connect(kb, board)
    try:
        return kb.dispatch_once(conn, spawn_fn=make_spawn(config_path, kb=kb), board=board)
    finally:
        conn.close()


def run(config_path: str, board: str | None, interval: float, once: bool) -> None:
    while True:
        result = dispatch_once(config_path, board)
        print(result, flush=True)
        if once:
            return
        time.sleep(max(0.5, interval))


def main() -> None:
    p = argparse.ArgumentParser(description="Run Hermes' canonical dispatcher with experimental worker spawns")
    p.add_argument("--config", required=True)
    p.add_argument("--board")
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--once", action="store_true")
    a = p.parse_args()
    run(a.config, a.board, a.interval, a.once)


if __name__ == "__main__":
    main()
