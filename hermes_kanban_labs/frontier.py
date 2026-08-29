from __future__ import annotations

from dataclasses import dataclass

from .config import LabConfig
from .policy import ResolvedExecutionPolicy

OPEN_STATUSES = ("triage", "todo", "ready", "running", "blocked", "review", "scheduled")


@dataclass(frozen=True)
class FrontierReport:
    open_cards: int
    ready_cards: int
    max_open_cards: int | None
    max_ready_cards: int | None
    over_open_budget: bool
    over_ready_budget: bool

    @property
    def saturated(self) -> bool:
        return self.over_open_budget or self.over_ready_budget


def inspect_frontier(conn, policy: ResolvedExecutionPolicy) -> FrontierReport:
    marks = ",".join("?" for _ in OPEN_STATUSES)
    open_cards = int(conn.execute(
        f"SELECT COUNT(*) FROM tasks WHERE status IN ({marks})", OPEN_STATUSES
    ).fetchone()[0])
    ready_cards = int(conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='ready'"
    ).fetchone()[0])
    return FrontierReport(
        open_cards=open_cards,
        ready_cards=ready_cards,
        max_open_cards=policy.max_open_cards,
        max_ready_cards=policy.max_ready_cards,
        over_open_budget=policy.max_open_cards is not None and open_cards >= policy.max_open_cards,
        over_ready_budget=policy.max_ready_cards is not None and ready_cards >= policy.max_ready_cards,
    )


def creation_guidance(report: FrontierReport, policy: ResolvedExecutionPolicy) -> str:
    pieces = [
        "KANBAN FRONTIER POLICY",
        f"open_cards={report.open_cards}" + (f"/{report.max_open_cards}" if report.max_open_cards else ""),
        f"ready_cards={report.ready_cards}" + (f"/{report.max_ready_cards}" if report.max_ready_cards else ""),
    ]
    if policy.max_children_per_card:
        pieces.append(f"max_children_per_card={policy.max_children_per_card}")
    if policy.max_depth:
        pieces.append(f"max_depth={policy.max_depth}")
    if report.saturated:
        pieces.append(
            "FRONTIER SATURATED: do not expand the graph. Finish, merge, archive, or explicitly block existing work before proposing more cards."
        )
    else:
        pieces.append(
            "Keep the frontier bounded. Prefer finishing or merging existing cards over creating speculative siblings. Never delete board history to reduce visual complexity."
        )
    return "\n".join(pieces)
