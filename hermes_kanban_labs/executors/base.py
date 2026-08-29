from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ExecutionSpec:
    model: str | None = None
    provider: str | None = None
    reasoning_effort: str | None = None
    skills: tuple[str, ...] = field(default_factory=tuple)
    workspace_kind: str | None = None


@dataclass
class ExecutionResult:
    returncode: int
    output: str
    metadata: dict = field(default_factory=dict)


class RunningExecution(Protocol):
    def wait(self) -> ExecutionResult: ...
    def cancel(self) -> None: ...
