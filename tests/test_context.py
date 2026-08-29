from types import SimpleNamespace

from hermes_kanban_labs.context import build_task_context


class Row(dict):
    pass


class Conn:
    def execute(self, sql, params):
        if "JOIN tasks p" in sql:
            return SimpleNamespace(fetchall=lambda: [Row(id="parent", title="P", status="done", result="ok")])
        if "JOIN tasks c" in sql:
            return SimpleNamespace(fetchall=lambda: [])
        if "task_comments" in sql:
            return SimpleNamespace(fetchall=lambda: [Row(author="a", body="note", created_at=1)])
        raise AssertionError(sql)


def test_context_is_snapshot_not_second_state():
    task = SimpleNamespace(id="t1", title="Do it", body="body", assignee="remote", workspace_kind="scratch", workspace_path=None, branch_name=None, skills=[], goal_mode=False)
    prompt = build_task_context(Conn(), task)
    assert '"id": "t1"' in prompt
    assert '"id": "parent"' in prompt
    assert '"body": "note"' in prompt
    assert "controlling Hermes instance owns the Kanban board" in prompt
