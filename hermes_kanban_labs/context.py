from __future__ import annotations

import json
from typing import Any


def _row_dict(row: Any) -> dict:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        return {}


def build_task_context(conn, task) -> str:
    """Build a read-only task snapshot from the canonical Hermes board.

    This is intentionally not a second state store. It reads the exact board
    the dispatcher already claimed from and serializes enough context for a
    remote worker that cannot mount the host's kanban.db.
    """
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
        "skills": list(getattr(task, "skills", None) or []),
        "goal_mode": bool(getattr(task, "goal_mode", False)),
        "parents": parents,
        "children": children,
        "comments": comments,
    }
    return (
        "You are a Hermes Kanban subworker. The controlling Hermes instance owns the "
        "Kanban board, task lifecycle, retries, and final completion. Work only on the "
        "task snapshot below. Do not claim you updated the host board yourself. Return "
        "a concise result with verification evidence.\n\n"
        "KANBAN TASK SNAPSHOT\n"
        + json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    )
