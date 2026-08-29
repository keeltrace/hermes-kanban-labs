from hermes_kanban_labs.config import WorkerConfig
from hermes_kanban_labs.executors.base import ExecutionSpec
from hermes_kanban_labs.executors.ssh_docker import _docker_command, _hermes_args


def test_cluster_is_one_hermes_container_pointing_at_one_gateway():
    w = WorkerConfig(
        name="monster", backend="ssh-docker", ssh="u@host", kind="shard_cluster",
        cluster_nodes=20, provider="openai-api", model="huge", base_url="http://10.0.0.50:8000/v1",
    )
    container, argv = _docker_command(w, "t_1", 7, "hello", None)
    joined = " ".join(argv)
    assert container.startswith("hkl-")
    assert argv.count("docker") == 1
    assert "OPENAI_BASE_URL=http://10.0.0.50:8000/v1" in argv
    assert "huge" in argv
    # Cluster cardinality is metadata for humans/control; there are not 20 Kanban spawns.
    assert "20" not in argv


def test_real_env_file_is_not_overridden_with_placeholder_key():
    w = WorkerConfig(
        name="w", backend="ssh-docker", ssh="u@h", provider="openai-api",
        model="m", base_url="http://x/v1", remote_env_file="/remote/worker.env",
    )
    _, argv = _docker_command(w, "t", 1, "p", None)
    assert "--env-file" in argv
    assert "OPENAI_API_KEY=local-not-a-secret" not in argv


def test_remote_shell_receives_one_safely_quoted_command(tmp_path, monkeypatch):
    import hermes_kanban_labs.executors.ssh_docker as mod
    calls = []
    class P:
        returncode = 0
        def communicate(self): return ("ok", None)
        def poll(self): return 0
    def fake_run(cmd, **kwargs):
        calls.append(("run", cmd)); return type("R", (), {"returncode":0,"stdout":"","stderr":""})()
    def fake_out(cmd, **kwargs):
        calls.append(("out", cmd)); return "/Users/test\n"
    def fake_popen(cmd, **kwargs):
        calls.append(("popen", cmd)); return P()
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setattr(mod.subprocess, "check_output", fake_out)
    monkeypatch.setattr(mod.subprocess, "Popen", fake_popen)
    w = WorkerConfig(name="w", backend="ssh-docker", ssh="u@mac", workspace="rsync", provider="openai-api", model="m")
    local = tmp_path / "workspace"; local.mkdir()
    mod.start(w, task_id="t1", run_id=1, prompt="quote ' and newline\nworks", workspace=str(local))
    popen_cmd = next(c[1] for c in calls if c[0] == "popen")
    assert popen_cmd[:2] == ["ssh", "u@mac"]
    assert len(popen_cmd) == 3
    assert "docker run" in popen_cmd[2]
    assert "/Users/test/.cache/hermes-kanban-labs" in popen_cmd[2]


def test_card_execution_spec_overrides_static_worker_model_and_carries_reasoning_skills():
    w = WorkerConfig(
        name="w", backend="ssh-docker", ssh="u@h", provider="worker-provider", model="worker-model"
    )
    spec = ExecutionSpec(
        model="card-model", provider="card-provider", reasoning_effort="high", skills=("git", "tests")
    )
    _, argv = _docker_command(w, "t", 9, "prompt", None, spec)
    assert "card-model" in argv and "worker-model" not in argv
    assert "card-provider" in argv and "worker-provider" not in argv
    assert argv[argv.index("--reasoning") + 1] == "high"
    assert argv.count("--skills") == 2
    assert "git" in argv and "tests" in argv


def test_execution_spec_keeps_upstream_workspace_kind():
    spec = ExecutionSpec(workspace_kind="worktree")
    assert spec.workspace_kind == "worktree"
