from __future__ import annotations

from pathlib import Path
import os

from hermes_kanban_labs.bridge import run_payload


class Conn:
    def close(self): pass


class FakeKB:
    def __init__(self): self.completed = []
    def connect(self, board=None): return Conn()
    def heartbeat_claim(self, *a, **k): return True
    def complete_task(self, conn, task_id, **kwargs):
        self.completed.append((task_id, kwargs)); return True


def _fake_path(tmp_path: Path, monkeypatch, docker_rc: int = 0):
    bindir = tmp_path / "bin"; bindir.mkdir()
    ssh = bindir / "ssh"
    ssh.write_text('''#!/bin/sh\nhost="$1"\nshift\n# HKL sends one safely quoted remote command string.\nexec sh -c "$1"\n''')
    docker = bindir / "docker"
    docker.write_text(f'''#!/bin/sh\necho "FAKE_REMOTE_HERMES_OK:$*"\nexit {docker_rc}\n''')
    ssh.chmod(0o755); docker.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ.get('PATH','')}")


def _cfg(tmp_path: Path):
    p = tmp_path / "workers.toml"
    p.write_text('''[runtime]\nheartbeat_seconds=10\n[workers.remote]\nbackend="ssh-docker"\nssh="fake-host"\nimage="nousresearch/hermes-agent:latest"\nprovider="openai-api"\nmodel="fake-model"\nbase_url="http://model-gateway:8000/v1"\nworkspace="none"\n''')
    return p


def _payload(config: Path):
    return {"config": str(config), "worker":"remote", "task_id":"t_smoke", "board":"default", "run_id":3, "claim_lock":"host:smoke", "prompt":"return smoke", "workspace":None}


def test_real_subprocess_smoke_bridge_to_ssh_to_docker_shim_to_completion(tmp_path, monkeypatch):
    _fake_path(tmp_path, monkeypatch, docker_rc=0)
    kb = FakeKB()
    rc = run_payload(_payload(_cfg(tmp_path)), kb=kb)
    assert rc == 0
    assert kb.completed
    result = kb.completed[0][1]["result"]
    assert "FAKE_REMOTE_HERMES_OK" in result
    assert "nousresearch/hermes-agent:latest" in result
    assert kb.completed[0][1]["expected_run_id"] == 3


def test_real_subprocess_smoke_remote_failure_does_not_complete(tmp_path, monkeypatch):
    _fake_path(tmp_path, monkeypatch, docker_rc=42)
    kb = FakeKB()
    rc = run_payload(_payload(_cfg(tmp_path)), kb=kb)
    assert rc == 42
    assert kb.completed == []
