from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from dataclasses import dataclass

from .base import ExecutionResult, ExecutionSpec
from ..config import WorkerConfig


def _safe_token(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in "-_")[-48:] or "task"


def _safe_ref_token(value: str) -> str:
    return _safe_token(value).replace("_", "-")


def _remote_home(target: str) -> str:
    return subprocess.check_output(["ssh", target, 'printf %s "$HOME"'], text=True).strip()


def _expand_remote_root(worker: WorkerConfig) -> str:
    root = worker.remote_root.rstrip("/")
    if worker.backend == "ssh-docker" and root.startswith("~/"):
        return f"{_remote_home(worker.ssh or '')}/{root[2:]}"
    return str(Path(root).expanduser()) if worker.backend == "local-docker" else root


def _git_output(workspace: str, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", workspace, *args], text=True, capture_output=True
    )
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "git command failed").strip())
    return (p.stdout or "").strip()


@dataclass(frozen=True)
class GitWorkspaceState:
    local_workspace: str
    base_head: str
    remote_bare: str
    remote_workspace: str
    remote_ref: str
    remote_branch: str
    local_result_ref: str


def _prepare_remote_git_workspace(
    worker: WorkerConfig,
    *,
    task_id: str,
    run_id: int | None,
    workspace: str,
) -> GitWorkspaceState:
    if worker.backend != "ssh-docker":
        raise RuntimeError("remote git workspace preparation requires ssh-docker")
    target = worker.ssh or ""
    local_workspace = str(Path(workspace).resolve())
    if _git_output(local_workspace, "rev-parse", "--is-inside-work-tree") != "true":
        raise RuntimeError(f"worker {worker.name}: workspace is not a Git worktree: {workspace}")
    base_head = _git_output(local_workspace, "rev-parse", "HEAD")
    common_dir_raw = _git_output(local_workspace, "rev-parse", "--git-common-dir")
    common_dir = Path(common_dir_raw)
    if not common_dir.is_absolute():
        common_dir = (Path(local_workspace) / common_dir).resolve()
    else:
        common_dir = common_dir.resolve()
    repo_key = hashlib.sha256(str(common_dir).encode()).hexdigest()[:16]
    root = _expand_remote_root(worker)
    bare = f"{root}/git/repos/{repo_key}.git"
    run_token = _safe_token(f"{task_id}-{run_id or 0}")
    remote_workspace = f"{root}/git/worktrees/{run_token}"
    remote_ref = f"refs/hermes-kanban-labs/runs/{run_token}"
    remote_branch = f"hkl-{run_token}"
    local_result_ref = f"refs/hermes-kanban-labs/results/{run_token}"

    with tempfile.TemporaryDirectory(prefix="hkl-git-") as td:
        bundle = Path(td) / "input.bundle"
        # Bundle the exact local HEAD so the remote host does not need access to
        # the controller's origin or private credentials.
        p = subprocess.run(
            ["git", "-C", local_workspace, "bundle", "create", str(bundle), "HEAD"],
            text=True, capture_output=True,
        )
        if p.returncode != 0:
            raise RuntimeError((p.stderr or p.stdout or "git bundle create failed").strip())
        remote_bundle = f"{root}/git/incoming/{run_token}.bundle"
        prep = (
            f"mkdir -p {shlex.quote(root + '/git/repos')} {shlex.quote(root + '/git/worktrees')} {shlex.quote(root + '/git/incoming')} && "
            f"(test -d {shlex.quote(bare)} || git init --bare {shlex.quote(bare)} >/dev/null) && "
            f"(git --git-dir={shlex.quote(bare)} worktree remove --force {shlex.quote(remote_workspace)} >/dev/null 2>&1 || true) && "
            f"rm -rf {shlex.quote(remote_workspace)}"
        )
        subprocess.run(["ssh", target, prep], check=True)
        subprocess.run(["scp", str(bundle), f"{target}:{remote_bundle}"], check=True)
        materialize = (
            f"git --git-dir={shlex.quote(bare)} fetch --force {shlex.quote(remote_bundle)} HEAD:{shlex.quote(remote_ref)} >/dev/null && "
            f"git --git-dir={shlex.quote(bare)} worktree add --force -B {shlex.quote(remote_branch)} "
            f"{shlex.quote(remote_workspace)} {shlex.quote(remote_ref)} >/dev/null && "
            f"rm -f {shlex.quote(remote_bundle)}"
        )
        subprocess.run(["ssh", target, materialize], check=True)

    # Overlay uncommitted and untracked controller files while keeping the
    # remote worktree's own .git administrative link intact.
    subprocess.run(
        [
            "rsync", "-az", "--delete", "--exclude=.git",
            f"{local_workspace}/", f"{target}:{remote_workspace}/",
        ],
        check=True,
    )
    return GitWorkspaceState(
        local_workspace=local_workspace,
        base_head=base_head,
        remote_bare=bare,
        remote_workspace=remote_workspace,
        remote_ref=remote_ref,
        remote_branch=remote_branch,
        local_result_ref=local_result_ref,
    )


def _cleanup_remote_git(target: str, state: GitWorkspaceState) -> None:
    cleanup = (
        f"(git --git-dir={shlex.quote(state.remote_bare)} worktree remove --force {shlex.quote(state.remote_workspace)} >/dev/null 2>&1 || "
        f"rm -rf {shlex.quote(state.remote_workspace)}) ; "
        f"git --git-dir={shlex.quote(state.remote_bare)} branch -D {shlex.quote(state.remote_branch)} >/dev/null 2>&1 || true; "
        f"git --git-dir={shlex.quote(state.remote_bare)} update-ref -d {shlex.quote(state.remote_ref)} >/dev/null 2>&1 || true"
    )
    subprocess.run(["ssh", target, cleanup], check=False)


def _cleanup_remote_workspace(target: str, remote_workspace: str) -> None:
    subprocess.run(["ssh", target, f"rm -rf {shlex.quote(remote_workspace)}"], check=False)

def _collect_remote_git_result(target: str, state: GitWorkspaceState) -> tuple[dict, str | None]:
    metadata: dict[str, str] = {"git_base_head": state.base_head}
    warning = None
    try:
        remote_head = subprocess.check_output(
            ["ssh", target, f"git -C {shlex.quote(state.remote_workspace)} rev-parse HEAD"],
            text=True,
        ).strip()
        metadata["git_remote_head"] = remote_head
        with tempfile.TemporaryDirectory(prefix="hkl-git-result-") as td:
            remote_bundle = f"{state.remote_workspace}/.hkl-result.bundle"
            local_bundle = Path(td) / "result.bundle"
            subprocess.run(
                ["ssh", target, f"git -C {shlex.quote(state.remote_workspace)} bundle create {shlex.quote(remote_bundle)} HEAD"],
                check=True,
            )
            subprocess.run(["scp", f"{target}:{remote_bundle}", str(local_bundle)], check=True)
            subprocess.run(
                [
                    "git", "-C", state.local_workspace, "fetch", "--force",
                    str(local_bundle), f"HEAD:{state.local_result_ref}",
                ],
                check=True,
            )
            metadata["git_result_ref"] = state.local_result_ref
    except Exception as exc:
        warning = f"git result capture failed: {exc}"
    finally:
        _cleanup_remote_git(target, state)
    return metadata, warning


@dataclass
class SSHDockerExecution:
    proc: subprocess.Popen
    target: str | None
    container: str
    remote_workspace: str | None
    local_workspace: str | None
    workspace_mode: str
    git_state: GitWorkspaceState | None = None

    def wait(self) -> ExecutionResult:
        out, _ = self.proc.communicate()
        text = out or ""
        metadata: dict = {}
        if self.workspace_mode in {"rsync", "git"} and self.target and self.remote_workspace and self.local_workspace:
            # Sync file changes back, but never overwrite controller Git metadata.
            sync = subprocess.run(
                ["rsync", "-az", "--exclude=.git", f"{self.target}:{self.remote_workspace}/", f"{self.local_workspace}/"],
                text=True, capture_output=True,
            )
            if sync.returncode != 0:
                text += f"\n[hermes-kanban-labs] rsync-back failed: {sync.stderr.strip()}\n"
                if self.workspace_mode == "git" and self.git_state:
                    _cleanup_remote_git(self.target, self.git_state)
                elif self.workspace_mode == "rsync":
                    _cleanup_remote_workspace(self.target, self.remote_workspace)
                return ExecutionResult(sync.returncode, text, metadata)
        if self.workspace_mode == "git" and self.target and self.git_state:
            git_meta, warning = _collect_remote_git_result(self.target, self.git_state)
            metadata.update(git_meta)
            if warning:
                text += f"\n[hermes-kanban-labs] {warning}\n"
                # File changes are already back. Preserve the worker result but
                # surface commit-capture degradation loudly in metadata/output.
                metadata["git_result_warning"] = warning
        elif self.workspace_mode == "rsync" and self.target and self.remote_workspace:
            _cleanup_remote_workspace(self.target, self.remote_workspace)
        return ExecutionResult(int(self.proc.returncode or 0), text, metadata)

    def cancel(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
        if self.target:
            subprocess.run(
                ["ssh", self.target, "docker", "rm", "-f", self.container],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
            if self.git_state:
                _cleanup_remote_git(self.target, self.git_state)
            elif self.workspace_mode == "rsync" and self.remote_workspace:
                _cleanup_remote_workspace(self.target, self.remote_workspace)
        else:
            subprocess.run(
                ["docker", "rm", "-f", self.container],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )


def _hermes_args(worker: WorkerConfig, prompt: str, spec: ExecutionSpec | None = None) -> list[str]:
    spec = spec or ExecutionSpec(model=worker.model, provider=worker.provider)
    args = ["--cli"]
    if spec.model:
        args += ["-m", spec.model]
    if spec.provider:
        args += ["--provider", spec.provider]
    if spec.reasoning_effort:
        args += ["--reasoning", spec.reasoning_effort]
    for skill in spec.skills:
        args += ["--skills", skill]
    args += ["chat", "-q", prompt]
    return args


def _docker_command(
    worker: WorkerConfig,
    task_id: str,
    run_id: int | None,
    prompt: str,
    remote_workspace: str | None,
    spec: ExecutionSpec | None = None,
) -> tuple[str, list[str]]:
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
        effective_provider = (spec.provider if spec else worker.provider)
        if effective_provider == "openai-api" and not worker.remote_env_file:
            # Local OpenAI-compatible gateways commonly require a syntactic key but
            # ignore its value. Never override a configured env file.
            argv += ["-e", "OPENAI_API_KEY=local-not-a-secret"]
    if remote_workspace:
        argv += ["-v", f"{remote_workspace}:/workspace", "-w", "/workspace"]
    argv += list(worker.extra_docker_args)
    argv += [worker.image, *_hermes_args(worker, prompt, spec)]
    return container, argv


def start(
    worker: WorkerConfig,
    *,
    task_id: str,
    run_id: int | None,
    prompt: str,
    workspace: str | None,
    spec: ExecutionSpec | None = None,
) -> SSHDockerExecution:
    remote_workspace = None
    git_state = None
    if worker.workspace in {"rsync", "git"}:
        if not workspace or not os.path.isdir(workspace):
            raise RuntimeError(f"worker {worker.name}: {worker.workspace} workspace requested but {workspace!r} is not a directory")
        if worker.workspace == "git" and (spec is None or spec.workspace_kind != "worktree"):
            raise RuntimeError(
                f"worker {worker.name}: workspace=git requires an upstream Hermes task workspace_kind='worktree'; "
                f"got {getattr(spec, 'workspace_kind', None)!r}"
            )
        if worker.backend == "local-docker":
            remote_workspace = str(Path(workspace).resolve())
            if worker.workspace == "git":
                _git_output(remote_workspace, "rev-parse", "--is-inside-work-tree")
        elif worker.workspace == "git":
            git_state = _prepare_remote_git_workspace(
                worker, task_id=task_id, run_id=run_id, workspace=workspace
            )
            remote_workspace = git_state.remote_workspace
        else:
            root = _expand_remote_root(worker)
            remote_workspace = f"{root}/{_safe_token(task_id)}-{run_id or 0}/workspace"
            mkdir_cmd = f"mkdir -p {shlex.quote(remote_workspace)}"
            subprocess.run(["ssh", worker.ssh or "", mkdir_cmd], check=True)
            subprocess.run(
                ["rsync", "-az", "--delete", "--exclude=.git", f"{Path(workspace).resolve()}/", f"{worker.ssh}:{remote_workspace}/"],
                check=True,
            )

    container, docker_argv = _docker_command(worker, task_id, run_id, prompt, remote_workspace, spec)
    if worker.backend == "local-docker":
        proc = subprocess.Popen(
            docker_argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
        target = None
    else:
        # Pass one shell-quoted command; prompt/task text never gets reparsed.
        remote_cmd = shlex.join(docker_argv)
        proc = subprocess.Popen(
            ["ssh", worker.ssh or "", remote_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
        target = worker.ssh
    return SSHDockerExecution(proc, target, container, remote_workspace, workspace, worker.workspace, git_state)


def doctor(worker: WorkerConfig, pull: bool = False) -> tuple[bool, str]:
    if worker.backend == "local-docker":
        prefix: list[str] = []
    else:
        prefix = ["ssh", worker.ssh or ""]
    checks = [
        [*prefix, "docker", "version", "--format", "{{.Server.Version}}"],
        [*prefix, "docker", "info", "--format", "{{.Architecture}}"],
    ]
    if worker.workspace == "git":
        checks.append([*prefix, "git", "--version"])
        if worker.backend == "ssh-docker":
            if not shutil_which("rsync") or not shutil_which("scp"):
                return False, "workspace=git requires local rsync and scp"
    lines = []
    for cmd in checks:
        p = subprocess.run(cmd, text=True, capture_output=True)
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "runtime check failed").strip()
        lines.append((p.stdout or "").strip())
    if pull:
        p = subprocess.run([*prefix, "docker", "pull", worker.image], text=True, capture_output=True)
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "docker pull failed").strip()
        lines.append(f"image={worker.image}")
    return True, " ".join(x for x in lines if x)


def shutil_which(name: str) -> str | None:
    import shutil
    return shutil.which(name)
