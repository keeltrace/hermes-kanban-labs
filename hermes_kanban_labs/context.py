from __future__ import annotations

import json
from typing import Any

from .frontier import FrontierReport, creation_guidance
from .policy import ResolvedExecutionPolicy


def _row_dict(row: Any) -> dict:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        return {}


def build_task_context(
    conn,
    task,
    *,
    policy: ResolvedExecutionPolicy | None = None,
    frontier: FrontierReport | None = None,
) -> str:
    """Build a read-only task snapshot from the canonical Hermes board.

    SQLite stays authoritative. The remote worker receives a serialized view
    plus resolved execution policy; it does not get a second task database.
    """
    if policy is None:
        policy = ResolvedExecutionPolicy(
            model=None, provider=None, reasoning_effort=None, skills=tuple(getattr(task, "skills", None) or ())
        )
    task_id = str(task.id)
    parents = []
    children = []
    comments = []
    try:
        rows = conn.execute(
            "SELECT p.id, p.title, p.status, p.result FROM task_links l "
            "JOIN tasks p ON p.id=l.parent_id WHERE l.child_id=? ORDER BY p.created_at",
            (task_id,),
        ).fetchall()
        parents = [_row_dict(r) for r in rows]
    except Exception:
        pass
    try:
        rows = conn.execute(
            "SELECT c.id, c.title, c.status, c.result FROM task_links l "
            "JOIN tasks c ON c.id=l.child_id WHERE l.parent_id=? ORDER BY c.created_at",
            (task_id,),
        ).fetchall()
        children = [_row_dict(r) for r in rows]
    except Exception:
        pass
    try:
        rows = conn.execute(
            "SELECT author, body, created_at FROM task_comments WHERE task_id=? ORDER BY created_at, rowid",
            (task_id,),
        ).fetchall()
        comments = [_row_dict(r) for r in rows]
    except Exception:
        pass

    payload = {
        "id": task_id,
        "title": getattr(task, "title", None),
        "body": getattr(task, "body", None),
        "assignee": getattr(task, "assignee", None),
        "workspace_kind": getattr(task, "workspace_kind", None),
        "workspace_path": getattr(task, "workspace_path", None),
        "branch_name": getattr(task, "branch_name", None),
        "workflow_template_id": getattr(task, "workflow_template_id", None),
        "current_step_key": getattr(task, "current_step_key", None),
        "skills": list(policy.skills),
        "goal_mode": bool(getattr(task, "goal_mode", False)),
        "execution": {
            "model": policy.model,
            "provider": policy.provider,
            "reasoning_effort": policy.reasoning_effort,
            "policy_sources": list(policy.sources),
        },
        "parents": parents,
        "children": children,
        "comments": comments,
    }

    sections = [
        "You are a Hermes Kanban subworker. The controlling Hermes instance owns the Kanban board; that board is canonical for task lifecycle, retries, and final completion.",
        "Work only on the task snapshot below. Preserve Git history when a Git workspace is present. Do not claim you updated the host board yourself. Return a concise result with verification evidence.",
    ]
    if policy.prompt_layers:
        sections.append("POLICY INSTRUCTIONS\n" + "\n\n".join(policy.prompt_layers))
    if frontier is not None:
        sections.append(creation_guidance(frontier, policy))
    sections.append("KANBAN TASK SNAPSHOT\n" + json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return "\n\n".join(sections)
