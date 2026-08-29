from pathlib import Path
import subprocess

from hermes_kanban_labs.executors.ssh_docker import _git_output


def _run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_git_bundle_of_exact_head_is_cloneable_without_origin_credentials(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.email", "test@example.com", cwd=repo)
    _run("git", "config", "user.name", "test", cwd=repo)
    (repo / "a.txt").write_text("one\n")
    _run("git", "add", "a.txt", cwd=repo)
    _run("git", "commit", "-qm", "base", cwd=repo)
    head = _git_output(str(repo), "rev-parse", "HEAD")
    bundle = tmp_path / "input.bundle"
    _run("git", "bundle", "create", str(bundle), "HEAD", cwd=repo)

    bare = tmp_path / "remote.git"
    _run("git", "init", "--bare", "-q", str(bare), cwd=tmp_path)
    _run("git", f"--git-dir={bare}", "fetch", str(bundle), "HEAD:refs/labs/run", cwd=tmp_path)
    assert subprocess.check_output(["git", f"--git-dir={bare}", "rev-parse", "refs/labs/run"], text=True).strip() == head

import pytest
from hermes_kanban_labs.config import WorkerConfig
from hermes_kanban_labs.executors.base import ExecutionSpec
from hermes_kanban_labs.executors.ssh_docker import start


def test_git_mode_requires_upstream_worktree_kind(tmp_path):
    repo = tmp_path / "repo2"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.email", "test@example.com", cwd=repo)
    _run("git", "config", "user.name", "test", cwd=repo)
    (repo / "a").write_text("x")
    _run("git", "add", "a", cwd=repo)
    _run("git", "commit", "-qm", "base", cwd=repo)
    worker = WorkerConfig(name="w", backend="local-docker", workspace="git")
    with pytest.raises(RuntimeError, match="workspace_kind='worktree'"):
        start(
            worker,
            task_id="t1",
            run_id=1,
            prompt="x",
            workspace=str(repo),
            spec=ExecutionSpec(workspace_kind="dir"),
        )

from hermes_kanban_labs.executors.ssh_docker import GitWorkspaceState, SSHDockerExecution


def test_git_sync_failure_still_cleans_remote_worktree_and_run_refs(monkeypatch, tmp_path):
    import hermes_kanban_labs.executors.ssh_docker as mod
    calls = []

    class Proc:
        returncode = 0
        def communicate(self):
            return ("worker output", None)
        def poll(self):
            return 0

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd and cmd[0] == "rsync":
            return type("R", (), {"returncode": 23, "stdout": "", "stderr": "sync failed"})()
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    state = GitWorkspaceState(
        local_workspace=str(tmp_path),
        base_head="abc",
        remote_bare="/remote/repo.git",
        remote_workspace="/remote/wt",
        remote_ref="refs/hermes-kanban-labs/runs/t-1",
        remote_branch="hkl-t-1",
        local_result_ref="refs/hermes-kanban-labs/results/t-1",
    )
    execution = SSHDockerExecution(
        proc=Proc(), target="u@h", container="c", remote_workspace="/remote/wt",
        local_workspace=str(tmp_path), workspace_mode="git", git_state=state,
    )
    result = execution.wait()
    assert result.returncode == 23
    ssh_cleanup = "\n".join(cmd[2] for cmd in calls if len(cmd) >= 3 and cmd[:2] == ["ssh", "u@h"])
    assert "worktree remove --force" in ssh_cleanup
    assert "branch -D hkl-t-1" in ssh_cleanup
    assert "update-ref -d refs/hermes-kanban-labs/runs/t-1" in ssh_cleanup
