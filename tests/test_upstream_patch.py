from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from hermes_kanban_labs.upstream_patch import apply_external_spawn_patch, UpstreamDriftError


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "upstream"
    (repo / "hermes_cli").mkdir(parents=True)
    src = Path(__file__).parent / "fixtures" / "current_main_snippets.txt"
    shutil.copy2(src, repo / "hermes_cli" / "kanban_db.py")
    return repo


def test_patch_current_main_seams_and_is_idempotent(tmp_path):
    repo = make_repo(tmp_path)
    first = apply_external_spawn_patch(repo)
    assert first.changed is True
    text = (repo / "hermes_cli" / "kanban_db.py").read_text()
    assert 'if spawn_fn is not None:\n            return any(row["assignee"] for row in review_rows)' in text
    assert 'if spawn_fn is None and profile_exists is not None and not profile_exists(row_assignee):' in text
    assert 'if spawn_fn is None and profile_exists is not None and not profile_exists(row["assignee"]):' in text
    assert 'if spawn_fn is not None:\n            _default_assignee_resolved = True' in text
    second = apply_external_spawn_patch(repo)
    assert second.changed is False
    assert second.before_sha256 == second.after_sha256


def test_patch_fails_closed_on_upstream_drift(tmp_path):
    repo = make_repo(tmp_path)
    p = repo / "hermes_cli" / "kanban_db.py"
    p.write_text(p.read_text().replace("def _any_spawnable_review", "def renamed_review_probe"))
    with pytest.raises(UpstreamDriftError):
        apply_external_spawn_patch(repo)
