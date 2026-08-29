from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import types

from hermes_kanban_labs.upstream_patch import apply_external_spawn_patch


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_custom_spawn_reaches_non_profile_lane_only_after_patch(tmp_path, monkeypatch):
    hermes_cli = types.ModuleType("hermes_cli")
    profiles = types.ModuleType("hermes_cli.profiles")
    profiles.profile_exists = lambda name: False
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.profiles", profiles)

    repo = tmp_path / "u"; (repo / "hermes_cli").mkdir(parents=True)
    src = Path(__file__).parent / "fixtures" / "current_main_snippets.txt"
    dst = repo / "hermes_cli" / "kanban_db.py"; shutil.copy2(src, dst)
    row = {"id":"t_ext", "assignee":"external-lane"}
    called = []
    spawn = lambda task, ws, board=None: called.append(task["id"])

    before = load(dst, "fixture_before")
    r0 = before.dispatch_once(None, spawn_fn=spawn, ready_rows=[row])
    assert r0.spawned == []
    assert r0.skipped_nonspawnable == ["t_ext"]
    assert called == []

    apply_external_spawn_patch(repo)
    after = load(dst, "fixture_after")
    r1 = after.dispatch_once(None, spawn_fn=spawn, ready_rows=[row])
    assert r1.skipped_nonspawnable == []
    assert r1.spawned == ["t_ext"]
    assert called == ["t_ext"]
