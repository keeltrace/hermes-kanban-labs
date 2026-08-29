from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
import json
from typing import Any


@dataclass(frozen=True)
class TreeCard:
    id: str
    title: str
    status: str
    assignee: str | None
    workflow: str | None
    path: str | None
    parents: tuple[str, ...]
    children: tuple[str, ...]


def _get(row: Any, key: str, default=None):
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)


def read_tree(conn) -> list[TreeCard]:
    rows = conn.execute(
        "SELECT id,title,status,assignee,workflow_template_id,current_step_key "
        "FROM tasks WHERE status != 'archived' ORDER BY created_at, id"
    ).fetchall()
    links = conn.execute(
        "SELECT parent_id, child_id FROM task_links ORDER BY parent_id, child_id"
    ).fetchall()
    parents: dict[str, list[str]] = defaultdict(list)
    children: dict[str, list[str]] = defaultdict(list)
    for link in links:
        parent = str(_get(link, "parent_id"))
        child = str(_get(link, "child_id"))
        parents[child].append(parent)
        children[parent].append(child)
    return [
        TreeCard(
            id=str(_get(row, "id")),
            title=str(_get(row, "title") or ""),
            status=str(_get(row, "status") or ""),
            assignee=_get(row, "assignee"),
            workflow=_get(row, "workflow_template_id"),
            path=_get(row, "current_step_key"),
            parents=tuple(parents[str(_get(row, "id"))]),
            children=tuple(children[str(_get(row, "id"))]),
        )
        for row in rows
    ]


def as_json(cards: list[TreeCard]) -> str:
    return json.dumps([asdict(card) for card in cards], indent=2, ensure_ascii=False)


def render_vertical(cards: list[TreeCard]) -> str:
    """Render workflow/path hierarchy vertically without inventing board state.

    `current_step_key` is treated as a dotted/slashed path projection. Parent-child
    task dependencies remain visible on each card as metadata rather than being
    confused with workflow-path nesting.
    """
    groups: dict[str, dict[tuple[str, ...], list[TreeCard]]] = defaultdict(lambda: defaultdict(list))
    for card in cards:
        workflow = card.workflow or "(no workflow)"
        raw_path = (card.path or "(no path)").replace("/", ".")
        parts = tuple(p for p in raw_path.split(".") if p) or ("(no path)",)
        groups[workflow][parts].append(card)

    lines: list[str] = []
    for workflow in sorted(groups):
        lines.append(f"workflow: {workflow}")
        paths = groups[workflow]
        seen: set[tuple[str, ...]] = set()
        for parts in sorted(paths):
            for depth in range(1, len(parts) + 1):
                prefix = parts[:depth]
                if prefix in seen:
                    continue
                seen.add(prefix)
                lines.append(f"{'  ' * depth}└─ {prefix[-1]}")
            indent = "  " * (len(parts) + 1)
            for card in paths[parts]:
                rel = []
                if card.parents:
                    rel.append("parents=" + ",".join(card.parents))
                if card.children:
                    rel.append("children=" + ",".join(card.children))
                relation = f"  [{' '.join(rel)}]" if rel else ""
                owner = f" @{card.assignee}" if card.assignee else ""
                lines.append(f"{indent}• {card.id} [{card.status}]{owner} {card.title}{relation}")
    return "\n".join(lines) if lines else "(empty board)"
