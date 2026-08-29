from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import tomllib


@dataclass(frozen=True)
class WorkerConfig:
    name: str
    backend: str
    ssh: str | None = None
    image: str = "nousresearch/hermes-agent:latest"
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    remote_env_file: str | None = None
    workspace: str = "none"  # none | rsync | git
    remote_root: str = "~/.cache/hermes-kanban-labs"
    network: str | None = None
    kind: str = "standalone"  # standalone | shard_cluster
    cluster_nodes: int | None = None
    extra_docker_args: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PolicyValues:
    model: str | None = None
    provider: str | None = None
    reasoning_effort: str | None = None
    prompt: str | None = None
    max_open_cards: int | None = None
    max_ready_cards: int | None = None
    max_children_per_card: int | None = None
    max_depth: int | None = None


@dataclass(frozen=True)
class WorkflowPolicy:
    values: PolicyValues = field(default_factory=PolicyValues)
    paths: dict[str, PolicyValues] = field(default_factory=dict)


@dataclass(frozen=True)
class BoardPolicy:
    values: PolicyValues = field(default_factory=PolicyValues)
    paths: dict[str, PolicyValues] = field(default_factory=dict)
    workflows: dict[str, WorkflowPolicy] = field(default_factory=dict)


@dataclass(frozen=True)
class LabConfig:
    workers: dict[str, WorkerConfig]
    heartbeat_seconds: int = 60
    claim_ttl_seconds: int | None = None
    policy: PolicyValues = field(default_factory=PolicyValues)
    boards: dict[str, BoardPolicy] = field(default_factory=dict)


def default_config_path() -> Path:
    raw = os.environ.get("HERMES_KANBAN_LABS_CONFIG")
    return Path(raw).expanduser() if raw else Path.home() / ".config" / "hermes-kanban-labs" / "workers.toml"


def _positive_optional(raw: dict[str, Any], key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    parsed = int(value)
    if parsed < 1:
        raise ValueError(f"{key} must be positive")
    return parsed


def _policy_values(raw: dict[str, Any] | None) -> PolicyValues:
    raw = raw or {}
    return PolicyValues(
        model=str(raw.get("model")).strip() if raw.get("model") else None,
        provider=str(raw.get("provider")).strip() if raw.get("provider") else None,
        reasoning_effort=str(raw.get("reasoning_effort")).strip() if raw.get("reasoning_effort") else None,
        prompt=str(raw.get("prompt")).strip() if raw.get("prompt") else None,
        max_open_cards=_positive_optional(raw, "max_open_cards"),
        max_ready_cards=_positive_optional(raw, "max_ready_cards"),
        max_children_per_card=_positive_optional(raw, "max_children_per_card"),
        max_depth=_positive_optional(raw, "max_depth"),
    )


def _paths(raw: Any) -> dict[str, PolicyValues]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("paths must be TOML tables")
    out: dict[str, PolicyValues] = {}
    for name, values in raw.items():
        key = str(name).strip().strip(".")
        if not key:
            raise ValueError("path key cannot be empty")
        if not isinstance(values, dict):
            raise ValueError(f"path {key!r} must be a TOML table")
        out[key] = _policy_values(values)
    return out


def _workflow(raw: dict[str, Any] | None) -> WorkflowPolicy:
    raw = raw or {}
    return WorkflowPolicy(values=_policy_values(raw), paths=_paths(raw.get("paths")))


def _board(raw: dict[str, Any] | None) -> BoardPolicy:
    raw = raw or {}
    workflows_raw = raw.get("workflows") or {}
    if not isinstance(workflows_raw, dict):
        raise ValueError("board workflows must be TOML tables")
    workflows = {
        str(name): _workflow(values if isinstance(values, dict) else {})
        for name, values in workflows_raw.items()
    }
    return BoardPolicy(
        values=_policy_values(raw),
        paths=_paths(raw.get("paths")),
        workflows=workflows,
    )


def _worker(name: str, raw: dict) -> WorkerConfig:
    backend = str(raw.get("backend", "ssh-docker")).strip()
    workspace = str(raw.get("workspace", "none")).strip()
    kind = str(raw.get("kind", "standalone")).strip()
    if backend not in {"ssh-docker", "local-docker"}:
        raise ValueError(f"worker {name!r}: unsupported backend {backend!r}")
    if backend == "ssh-docker" and not str(raw.get("ssh", "")).strip():
        raise ValueError(f"worker {name!r}: ssh is required for ssh-docker")
    if workspace not in {"none", "rsync", "git"}:
        raise ValueError(f"worker {name!r}: workspace must be 'none', 'rsync', or 'git'")
    if kind not in {"standalone", "shard_cluster"}:
        raise ValueError(f"worker {name!r}: kind must be standalone or shard_cluster")
    extra = raw.get("extra_docker_args", [])
    if not isinstance(extra, list) or not all(isinstance(x, str) for x in extra):
        raise ValueError(f"worker {name!r}: extra_docker_args must be a string list")
    cluster_nodes = raw.get("cluster_nodes")
    if cluster_nodes is not None:
        cluster_nodes = int(cluster_nodes)
        if cluster_nodes < 1:
            raise ValueError(f"worker {name!r}: cluster_nodes must be positive")
    return WorkerConfig(
        name=name,
        backend=backend,
        ssh=str(raw.get("ssh")).strip() if raw.get("ssh") else None,
        image=str(raw.get("image", "nousresearch/hermes-agent:latest")).strip(),
        provider=str(raw.get("provider")).strip() if raw.get("provider") else None,
        model=str(raw.get("model")).strip() if raw.get("model") else None,
        base_url=str(raw.get("base_url")).strip() if raw.get("base_url") else None,
        remote_env_file=str(raw.get("remote_env_file")).strip() if raw.get("remote_env_file") else None,
        workspace=workspace,
        remote_root=str(raw.get("remote_root", "~/.cache/hermes-kanban-labs")).strip(),
        network=str(raw.get("network")).strip() if raw.get("network") else None,
        kind=kind,
        cluster_nodes=cluster_nodes,
        extra_docker_args=tuple(extra),
    )


def load_config(path: str | Path | None = None) -> LabConfig:
    p = Path(path).expanduser() if path else default_config_path()
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    workers_raw = data.get("workers") or {}
    if not isinstance(workers_raw, dict) or not workers_raw:
        raise ValueError(f"{p}: define at least one [workers.<name>] table")
    workers = {name: _worker(name, raw or {}) for name, raw in workers_raw.items()}
    runtime = data.get("runtime") or {}
    hb = int(runtime.get("heartbeat_seconds", 60))
    if hb < 1:
        raise ValueError("runtime.heartbeat_seconds must be positive")
    ttl = runtime.get("claim_ttl_seconds")
    boards_raw = data.get("boards") or {}
    if not isinstance(boards_raw, dict):
        raise ValueError("boards must be TOML tables")
    return LabConfig(
        workers=workers,
        heartbeat_seconds=hb,
        claim_ttl_seconds=int(ttl) if ttl is not None else None,
        policy=_policy_values(data.get("policy") or {}),
        boards={str(name): _board(raw if isinstance(raw, dict) else {}) for name, raw in boards_raw.items()},
    )
