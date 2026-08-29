from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import threading

from .config import load_config
from .executors.ssh_docker import start as start_execution


class ClaimLost(RuntimeError):
    pass


def _connect(kb, board: str | None):
    try:
        return kb.connect(board=board)
    except TypeError:
        if board:
            os.environ["HERMES_KANBAN_BOARD"] = board
        return kb.connect()


def run_payload(payload: dict, *, kb=None, executor_start=start_execution) -> int:
    if kb is None:
        from hermes_cli import kanban_db as kb  # type: ignore

    cfg = load_config(payload["config"])
    worker = cfg.workers[payload["worker"]]
    task_id = str(payload["task_id"])
    board = payload.get("board")
    run_id = payload.get("run_id")
    claim_lock = payload.get("claim_lock")
    prompt = payload["prompt"]
    workspace = payload.get("workspace") or None
    if not claim_lock:
        raise RuntimeError("bridge payload is missing the upstream claim_lock")

    execution = executor_start(
        worker, task_id=task_id, run_id=run_id, prompt=prompt, workspace=workspace
    )
    stop = threading.Event()
    claim_lost = threading.Event()

    def heartbeat() -> None:
        # One connection per thread; sqlite connections are not shared across threads.
        while not stop.wait(cfg.heartbeat_seconds):
            conn = _connect(kb, board)
            try:
                owned = kb.heartbeat_claim(
                    conn, task_id,
                    ttl_seconds=cfg.claim_ttl_seconds,
                    claimer=claim_lock,
                )
            finally:
                conn.close()
            if not owned:
                claim_lost.set()
                execution.cancel()
                return

    thread = threading.Thread(target=heartbeat, name=f"hkl-heartbeat-{task_id}", daemon=True)
    thread.start()

    previous = {}
    def cancel_signal(signum, _frame):
        execution.cancel()
        raise SystemExit(128 + int(signum))
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous[sig] = signal.signal(sig, cancel_signal)
        except (ValueError, OSError):
            pass

    try:
        result = execution.wait()
    finally:
        stop.set()
        thread.join(timeout=2)
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass

    if claim_lost.is_set():
        # Fail closed. A stale bridge must never complete a successor run.
        return 75
    if result.returncode != 0:
        # Deliberately leave the card `running`; the bridge process exits nonzero and
        # upstream Hermes' existing crashed-worker/failure-breaker logic owns retry.
        return int(result.returncode)

    output = (result.output or "").strip()
    if len(output) > 12000:
        output = output[-12000:]
    conn = _connect(kb, board)
    try:
        completed = kb.complete_task(
            conn,
            task_id,
            result=output or "Remote Hermes worker completed successfully.",
            summary=(output[-2000:] if output else "Remote Hermes worker completed successfully."),
            metadata={
                "hermes_kanban_labs": {
                    "worker": worker.name,
                    "kind": worker.kind,
                    "cluster_nodes": worker.cluster_nodes,
                }
            },
            expected_run_id=int(run_id) if run_id is not None else None,
        )
    finally:
        conn.close()
    return 0 if completed else 75


def main() -> None:
    p = argparse.ArgumentParser(description="Local lifecycle bridge for one experimental Hermes Kanban worker")
    p.add_argument("payload", help="Path to dispatcher-generated JSON payload")
    args = p.parse_args()
    payload_path = Path(args.payload)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    try:
        payload_path.unlink()
    except OSError:
        pass
    raise SystemExit(run_payload(payload))


if __name__ == "__main__":
    main()
