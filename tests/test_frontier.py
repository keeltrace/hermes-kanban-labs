import sqlite3

from hermes_kanban_labs.frontier import inspect_frontier, creation_guidance
from hermes_kanban_labs.policy import ResolvedExecutionPolicy


def _policy(**kwargs):
    return ResolvedExecutionPolicy(model=None, provider=None, reasoning_effort=None, skills=(), **kwargs)


def test_frontier_saturates_without_mutating_board():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT, status TEXT)")
    conn.executemany("INSERT INTO tasks VALUES (?,?)", [("a","ready"),("b","running"),("c","done")])
    before = conn.total_changes
    p = _policy(max_open_cards=2, max_ready_cards=2, max_children_per_card=3, max_depth=4)
    report = inspect_frontier(conn, p)
    assert report.open_cards == 2
    assert report.ready_cards == 1
    assert report.saturated is True
    assert conn.total_changes == before
    guide = creation_guidance(report, p)
    assert "do not expand the graph" in guide
    assert "Never delete" not in guide  # saturated branch is stronger and shorter
