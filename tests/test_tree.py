import sqlite3

from hermes_kanban_labs.tree import read_tree, render_vertical


def test_vertical_tree_projects_workflow_paths_and_dependency_links():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript('''
      CREATE TABLE tasks (
        id TEXT, title TEXT, status TEXT, assignee TEXT,
        workflow_template_id TEXT, current_step_key TEXT, created_at INTEGER
      );
      CREATE TABLE task_links (parent_id TEXT, child_id TEXT);
    ''')
    conn.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)", [
        ("t1","Explore options","ready","researcher","release","research",1),
        ("t2","Deep benchmark","todo","bench","release","research.deep",2),
        ("t3","Implement","todo","coder","release","implementation.backend",3),
    ])
    conn.execute("INSERT INTO task_links VALUES ('t1','t2')")
    cards = read_tree(conn)
    text = render_vertical(cards)
    assert "workflow: release" in text
    assert "└─ research" in text
    assert "└─ deep" in text
    assert "t2 [todo] @bench Deep benchmark" in text
    assert "parents=t1" in text
    assert "children=t2" in text
