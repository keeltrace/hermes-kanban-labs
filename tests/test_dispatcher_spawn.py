from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import hermes_kanban_labs.dispatcher as d


class Conn:
    def execute(self, sql, params):
        return SimpleNamespace(fetchall=lambda: [])
    def close(self):
        pass


class KB:
    def __init__(self):
        self.default_called = 0
    def _default_spawn(self, task, workspace, *, board=None):
        self.default_called += 1
        return 111
    def connect(self, board=None):
        return Conn()
    def worker_logs_dir(self, board=None):
        p = Path(self.tmp) / "logs"; p.mkdir(parents=True, exist_ok=True); return p


def write_cfg(tmp_path):
    p = tmp_path / "w.toml"
    p.write_text('[workers.remote]\nbackend="ssh-docker"\nssh="u@h"\n')
    return p


def task(assignee):
    return SimpleNamespace(id="t1", assignee=assignee, current_run_id=2, claim_lock="h:l", title="x", body="y", workspace_kind="scratch", workspace_path=None, branch_name=None, skills=[], goal_mode=False)


def test_mixed_mode_preserves_upstream_default_spawn(tmp_path):
    kb = KB(); kb.tmp = tmp_path
    spawn = d.make_spawn(str(write_cfg(tmp_path)), kb=kb)
    assert spawn(task("ordinary-profile"), str(tmp_path), board="default") == 111
    assert kb.default_called == 1


def test_remote_lane_returns_local_bridge_pid(tmp_path, monkeypatch):
    kb = KB(); kb.tmp = tmp_path
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    captured = {}
    class Proc:
        pid = 4242
    def popen(cmd, **kwargs):
        captured["cmd"] = cmd; captured["kwargs"] = kwargs
        return Proc()
    monkeypatch.setattr(d.subprocess, "Popen", popen)
    spawn = d.make_spawn(str(write_cfg(tmp_path)), kb=kb)
    pid = spawn(task("remote"), str(tmp_path), board="default")
    assert pid == 4242
    assert "hermes_kanban_labs.bridge" in captured["cmd"]
    assert kb.default_called == 0
