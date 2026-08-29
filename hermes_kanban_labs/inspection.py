from __future__ import annotations

from types import SimpleNamespace

from .config import LabConfig, WorkerConfig
from .policy import resolve_execution_policy


def resolve_scope_policy(
    cfg: LabConfig,
    *,
    board: str = "default",
    workflow: str | None = None,
    path: str | None = None,
):
    """Resolve policy for board/workflow/path inspection with no card override."""
    worker = WorkerConfig(name="__scope__", backend="local-docker")
    task = SimpleNamespace(
        workflow_template_id=workflow,
        current_step_key=path,
        model_override=None,
        provider_override=None,
        reasoning_effort=None,
        skills=[],
    )
    return resolve_execution_policy(cfg, worker, task, board)
