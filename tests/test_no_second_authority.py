from pathlib import Path


def test_package_does_not_create_its_own_sqlite_board_or_scheduler():
    root = Path(__file__).parents[1] / "hermes_kanban_labs"
    source = "\n".join(p.read_text(errors="ignore") for p in root.rglob("*.py"))
    assert "sqlite3.connect" not in source
    assert "CREATE TABLE tasks" not in source
    assert "class Scheduler" not in source
