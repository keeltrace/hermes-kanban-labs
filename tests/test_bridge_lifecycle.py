from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time

from hermes_kanban_labs.bridge import run_payload
from hermes_kanban_labs.executors.base import ExecutionResult


class Conn:
    def close(self):
        pass


class FakeKB:
    def __init__(self, heartbeat=True):
        self.heartbeat_value = heartbeat
        self.completed = []
        self.heartbeats = 0
    def connect(self, board=None):
        return Conn()
    def heartbeat_claim(self, conn, task_id, *, ttl_seconds=None, claimer=None):
        self.heartbeats += 1
        return self.heartbeat_value
    def complete_task(self, conn, task_id, **kwargs):
        self.completed.append((task_id, kwargs))
        return True


@dataclass
class FakeRun:
    delay: float
    code: int
    text: str
    cancelled: bool = False
    def wait(self):
        deadline = time.time() + self.delay
        while time.time() < deadline and not self.cancelled:
            time.sleep(0.01)
        return ExecutionResult(143 if self.cancelled else self.code, self.text)
    def cancel(self):
        self.cancelled = True


def cfg(tmp_path: Path, heartbeat=1):
    p = tmp_path / "workers.toml"
    p.write_text(f'''[runtime]\nheartbeat_seconds={heartbeat}\n[workers.remote]\nbackend="ssh-docker"\nssh="u@h"\nprovider="openai-api"\nmodel="m"\nbase_url="http://x/v1"\n''')
    return p


def payload(p):
    return {"config": str(p), "worker": "remote", "task_id": "t1", "board": "default", "run_id": 9, "claim_lock": "host:lock", "prompt": "do work", "workspace": None}


def test_success_completes_exact_run(tmp_path):
    kb = FakeKB()
    run = FakeRun(0.01, 0, "verified result")
    rc = run_payload(payload(cfg(tmp_path)), kb=kb, executor_start=lambda *a, **k: run)
    assert rc == 0
    assert len(kb.completed) == 1
    assert kb.completed[0][1]["expected_run_id"] == 9
    assert kb.completed[0][1]["result"] == "verified result"


def test_remote_failure_leaves_upstream_lifecycle_authoritative(tmp_path):
    kb = FakeKB()
    run = FakeRun(0.01, 23, "remote docker failed")
    rc = run_payload(payload(cfg(tmp_path)), kb=kb, executor_start=lambda *a, **k: run)
    assert rc == 23
    assert kb.completed == []


def test_lost_claim_cancels_remote_and_never_completes_successor(tmp_path):
    kb = FakeKB(heartbeat=False)
    run = FakeRun(1.5, 0, "too late")
    rc = run_payload(payload(cfg(tmp_path, heartbeat=1)), kb=kb, executor_start=lambda *a, **k: run)
    assert rc == 75
    assert run.cancelled is True
    assert kb.completed == []
    assert kb.heartbeats >= 1


def test_bridge_preserves_workspace_kind_and_card_execution_spec(tmp_path):
    kb = FakeKB()
    run = FakeRun(0.01, 0, "ok")
    seen = {}
    pl = payload(cfg(tmp_path))
    pl["workspace_kind"] = "worktree"
    pl["execution"] = {
        "model": "card-model",
        "provider": "card-provider",
        "reasoning_effort": "high",
        "skills": ["git", "tests"],
        "policy_sources": ["card:model_override"],
    }
    def start(*args, **kwargs):
        seen.update(kwargs)
        return run
    rc = run_payload(pl, kb=kb, executor_start=start)
    assert rc == 0
    spec = seen["spec"]
    assert spec.workspace_kind == "worktree"
    assert spec.model == "card-model"
    assert spec.provider == "card-provider"
    assert spec.reasoning_effort == "high"
    assert spec.skills == ("git", "tests")
