from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
from dataclasses import dataclass

from .base import ExecutionResult
from ..config import WorkerConfig


def _safe_token(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in "-_")[-48:] or "task"


def _remote_expand(path: str) -> str:
    # Expansion happens on the remote shell; quote everything except a leading ~/.
    if path.startswith("~/"):
        return "$HOME/" + shlex.quote(path[2:])
    return shlex.quote(path)


@dataclass
class SSHDockerExecution:
    proc: subprocess.Popen
    target: str | None
    container: str
    remote_workspace: str | None
    local_workspace: str | None
    workspace_mode: str

    def wait(self) -> ExecutionResult:
        out, _ = self.proc.communicate()
        text = out or ""
        if self.workspace_mode == "rsync" and self.target and self.remote_workspace and self.local_workspace:
            # Best effort only after the worker has stopped. rsync failures are surfaced
            # in output and turn the execution into a failure rather than silently losing work.
            sync = subprocess.run(
                ["rsync", "-az", "--exclude=.git/", f"{self.target}:{self.remote_workspace}/", f"{self.local_workspace}/"],
                text=True, capture_output=True,
            )
            if sync.returncode != 0:
                text += f"\n[hermes-kanban-labs] rsync-back failed: {sync.stderr.strip()}\n"
                return ExecutionResult(sync.returncode, text)
        return ExecutionResult(int(self.proc.returncode or 0), text)

    def cancel(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
        if self.target:
            subprocess.run(
                ["ssh", self.target, "docker", "rm", "-f", self.container],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
        else:
            subprocess.run(
                ["docker", "rm", "-f", self.container],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )


def _hermes_args(worker: WorkerConfig, prompt: str) -> list[str]:
    args = ["--cli"]
    if worker.model:
        args += ["-m", worker.model]
    if worker.provider:
        args += ["--provider", worker.provider]
    args += ["chat", "-q", prompt]
    return args


def _docker_command(worker: WorkerConfig, task_id: str, run_id: int | None, prompt: str, remote_workspace: str | None) -> tuple[str, list[str]]:
    suffix = _safe_token(f"{task_id}-{run_id or 0}")
    container = f"hkl-{suffix}"
    argv = ["docker", "run", "--rm", "--name", container, "--label", "hermes-kanban-labs.worker=true"]
    argv += ["--label", f"hermes-kanban-labs.task={task_id}"]
    if worker.network:
        argv += ["--network", worker.network]
    if worker.remote_env_file:
        argv += ["--env-file", worker.remote_env_file]
    if worker.base_url:
        argv += ["-e", f"OPENAI_BASE_URL={worker.base_url}"]
        if worker.provider == "openai-api" and not worker.remote_env_file:
            # Local OpenAI-compatible gateways commonly require a syntactic key but
            # ignore its value. Never override a configured env file.
            argv += ["-e", "OPENAI_API_KEY=local-not-a-secret"]
    if remote_workspace:
        argv += ["-v", f"{remote_workspace}:/workspace", "-w", "/workspace"]
    argv += list(worker.extra_docker_args)
    argv += [worker.image, *_hermes_args(worker, prompt)]
    return container, argv


def start(worker: WorkerConfig, *, task_id: str, run_id: int | None, prompt: str, workspace: str | None) -> SSHDockerExecution:
    remote_workspace = None
    if worker.workspace == "rsync":
        if not workspace or not os.path.isdir(workspace):
            raise RuntimeError(f"worker {worker.name}: rsync workspace requested but {workspace!r} is not a directory")
        if worker.backend == "local-docker":
            remote_workspace = str(Path(workspace).resolve())
        else:
            remote_workspace = f"{worker.remote_root.rstrip('/')}/{_safe_token(task_id)}-{run_id or 0}/workspace"
            # Resolve ~/ before it is passed to Docker; Docker itself does not
            # expand shell tildes in a -v source path.
            if remote_workspace.startswith("~/"):
                home = subprocess.check_output(
                    ["ssh", worker.ssh or "", 'printf %s "$HOME"'], text=True
                ).strip()
                remote_workspace = f"{home}/{remote_workspace[2:]}"
            mkdir_cmd = f"mkdir -p {shlex.quote(remote_workspace)}"
            subprocess.run(["ssh", worker.ssh or "", mkdir_cmd], check=True)
            subprocess.run(
                ["rsync", "-az", "--delete", "--exclude=.git/", f"{Path(workspace).resolve()}/", f"{worker.ssh}:{remote_workspace}/"],
                check=True,
            )

    container, docker_argv = _docker_command(worker, task_id, run_id, prompt, remote_workspace)
    if worker.backend == "local-docker":
        proc = subprocess.Popen(
            docker_argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
        target = None
    else:
        # Pass one shell-quoted command after `--`; no user task text is interpreted
        # by the remote shell because shlex.join quotes every argv element.
        remote_cmd = shlex.join(docker_argv)
        proc = subprocess.Popen(
            ["ssh", worker.ssh or "", remote_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
        target = worker.ssh
    return SSHDockerExecution(proc, target, container, remote_workspace, workspace, worker.workspace)


def doctor(worker: WorkerConfig, pull: bool = False) -> tuple[bool, str]:
    if worker.backend == "local-docker":
        prefix: list[str] = []
    else:
        prefix = ["ssh", worker.ssh or ""]
    checks = [
        [*prefix, "docker", "version", "--format", "{{.Server.Version}}"],
        [*prefix, "docker", "info", "--format", "{{.Architecture}}"],
    ]
    lines = []
    for cmd in checks:
        p = subprocess.run(cmd, text=True, capture_output=True)
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "docker check failed").strip()
        lines.append((p.stdout or "").strip())
    if pull:
        p = subprocess.run([*prefix, "docker", "pull", worker.image], text=True, capture_output=True)
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "docker pull failed").strip()
        lines.append(f"image={worker.image}")
    return True, " ".join(x for x in lines if x)
