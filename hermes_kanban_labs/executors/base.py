from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExecutionResult:
    returncode: int
    output: str


class RunningExecution(Protocol):
    def wait(self) -> ExecutionResult: ...
    def cancel(self) -> None: ...
