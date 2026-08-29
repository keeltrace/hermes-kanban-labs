from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .config import LabConfig, PolicyValues, WorkerConfig


@dataclass(frozen=True)
class ResolvedExecutionPolicy:
    model: str | None
    provider: str | None
    reasoning_effort: str | None
    skills: tuple[str, ...]
    prompt_layers: tuple[str, ...] = field(default_factory=tuple)
    sources: tuple[str, ...] = field(default_factory=tuple)
    max_open_cards: int | None = None
    max_ready_cards: int | None = None
    max_children_per_card: int | None = None
    max_depth: int | None = None


def _overlay(current: dict[str, Any], values: PolicyValues, source: str) -> None:
    changed = False
    for key in (
        "model", "provider", "reasoning_effort",
        "max_open_cards", "max_ready_cards", "max_children_per_card", "max_depth",
    ):
        value = getattr(values, key)
        if value is not None:
            current[key] = value
            changed = True
    if values.prompt:
        current.setdefault("prompt_layers", []).append(values.prompt)
        changed = True
    if changed:
        current.setdefault("sources", []).append(source)


def _matching_paths(step: str | None, paths: dict[str, PolicyValues]) -> list[tuple[str, PolicyValues]]:
    if not step:
        return []
    step = step.strip().strip(".")
    matches = []
    for key, values in paths.items():
        if step == key or step.startswith(key + "."):
            matches.append((key, values))
    return sorted(matches, key=lambda item: (item[0].count("."), len(item[0])))


def resolve_execution_policy(cfg: LabConfig, worker: WorkerConfig, task, board: str | None) -> ResolvedExecutionPolicy:
    current: dict[str, Any] = {
        "model": worker.model,
        "provider": worker.provider,
        "reasoning_effort": None,
        "prompt_layers": [],
        "sources": [f"worker:{worker.name}"],
        "max_open_cards": None,
        "max_ready_cards": None,
        "max_children_per_card": None,
        "max_depth": None,
    }
    _overlay(current, cfg.policy, "policy:global")

    board_name = board or "default"
    board_policy = cfg.boards.get(board_name)
    workflow_id = getattr(task, "workflow_template_id", None)
    step = getattr(task, "current_step_key", None)
    if board_policy:
        _overlay(current, board_policy.values, f"board:{board_name}")
        if workflow_id and workflow_id in board_policy.workflows:
            workflow = board_policy.workflows[workflow_id]
            _overlay(current, workflow.values, f"workflow:{workflow_id}")
        else:
            workflow = None
        for key, values in _matching_paths(step, board_policy.paths):
            _overlay(current, values, f"board-path:{key}")
        if workflow:
            for key, values in _matching_paths(step, workflow.paths):
                _overlay(current, values, f"workflow-path:{workflow_id}:{key}")

    # Native Hermes card overrides are the final authority.
    if getattr(task, "model_override", None):
        current["model"] = task.model_override
        current["sources"].append("card:model_override")
    if getattr(task, "provider_override", None):
        current["provider"] = task.provider_override
        current["sources"].append("card:provider_override")
    if getattr(task, "reasoning_effort", None):
        current["reasoning_effort"] = task.reasoning_effort
        current["sources"].append("card:reasoning_effort")

    skills = tuple(dict.fromkeys(str(x) for x in (getattr(task, "skills", None) or []) if x))
    return ResolvedExecutionPolicy(
        model=current["model"],
        provider=current["provider"],
        reasoning_effort=current["reasoning_effort"],
        skills=skills,
        prompt_layers=tuple(current["prompt_layers"]),
        sources=tuple(current["sources"]),
        max_open_cards=current["max_open_cards"],
        max_ready_cards=current["max_ready_cards"],
        max_children_per_card=current["max_children_per_card"],
        max_depth=current["max_depth"],
    )
