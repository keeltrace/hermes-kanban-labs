def dispatch_once(conn, *, spawn_fn=None, default_assignee=None, ready_rows=None, review_rows=None):
    review_rows = list(review_rows or [])
    ready_rows = list(ready_rows or [])
    result = type("R", (), {"skipped_nonspawnable": [], "spawned": []})()

    def _any_spawnable_review() -> bool:
        if not review_rows:
            return False
        try:
            from hermes_cli.profiles import profile_exists as _rpe
        except Exception:
            return any(row["assignee"] for row in review_rows)
        return any(
            row["assignee"] and _rpe(row["assignee"]) for row in review_rows
        )

    _default_assignee = (default_assignee or "").strip() or None
    _default_assignee_resolved = False
    if _default_assignee:
        try:
            from hermes_cli.profiles import profile_exists as _pe
            _default_assignee_resolved = bool(_pe(_default_assignee))
        except Exception:
            # Profiles module not importable (test stubs, exotic envs).
            # Trust the operator's config and try the assignment; the
            # downstream profile_exists check on the assigned row will
            # bucket it as nonspawnable if the profile genuinely isn't
            # there, with the existing diagnostic.
            _default_assignee_resolved = True

    for row in ready_rows:
        row_assignee = row["assignee"]
        try:
            from hermes_cli.profiles import profile_exists  # local import: avoids cycle
        except Exception:
            profile_exists = None  # type: ignore[assignment]
        if profile_exists is not None and not profile_exists(row_assignee):
            result.skipped_nonspawnable.append(row["id"])
            continue
        if spawn_fn is not None:
            spawn_fn(row, "/tmp", board=None)
            result.spawned.append(row["id"])

    for row in review_rows:
        try:
            from hermes_cli.profiles import profile_exists
        except Exception:
            profile_exists = None  # type: ignore[assignment]
        if profile_exists is not None and not profile_exists(row["assignee"]):
            result.skipped_nonspawnable.append(row["id"])
            continue
        if spawn_fn is not None:
            spawn_fn(row, "/tmp", board=None)
            result.spawned.append(row["id"])
    return result


def _default_spawn(task, workspace, *, board=None):
    return 123


def heartbeat_claim(conn, task_id, *, ttl_seconds=None, claimer=None):
    return True


def complete_task(conn, task_id, *, result=None, summary=None, metadata=None, expected_run_id=None):
    return True
