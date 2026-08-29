from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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
    workspace: str = "none"  # none | rsync
    remote_root: str = "~/.cache/hermes-kanban-labs"
    network: str | None = None
    kind: str = "standalone"  # standalone | shard_cluster
    cluster_nodes: int | None = None
    extra_docker_args: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LabConfig:
    workers: dict[str, WorkerConfig]
    heartbeat_seconds: int = 60
    claim_ttl_seconds: int | None = None


def default_config_path() -> Path:
    raw = os.environ.get("HERMES_KANBAN_LABS_CONFIG")
    return Path(raw).expanduser() if raw else Path.home() / ".config" / "hermes-kanban-labs" / "workers.toml"


def _worker(name: str, raw: dict) -> WorkerConfig:
    backend = str(raw.get("backend", "ssh-docker")).strip()
    workspace = str(raw.get("workspace", "none")).strip()
    kind = str(raw.get("kind", "standalone")).strip()
    if backend not in {"ssh-docker", "local-docker"}:
        raise ValueError(f"worker {name!r}: unsupported backend {backend!r}")
    if backend == "ssh-docker" and not str(raw.get("ssh", "")).strip():
        raise ValueError(f"worker {name!r}: ssh is required for ssh-docker")
    if workspace not in {"none", "rsync"}:
        raise ValueError(f"worker {name!r}: workspace must be 'none' or 'rsync'")
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
    return LabConfig(
        workers=workers,
        heartbeat_seconds=hb,
        claim_ttl_seconds=int(ttl) if ttl is not None else None,
    )
