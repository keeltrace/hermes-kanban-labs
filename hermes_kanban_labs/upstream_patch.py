from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib


class UpstreamDriftError(RuntimeError):
    pass


@dataclass(frozen=True)
class PatchResult:
    changed: bool
    before_sha256: str
    after_sha256: str
    path: Path


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def apply_external_spawn_patch(repo: str | Path, *, write: bool = True) -> PatchResult:
    """Make current Hermes `spawn_fn` usable for non-profile assignees.

    Stock behavior is unchanged when spawn_fn is None. This is intentionally
    tiny and should be deleted as soon as upstream #70547 lands an equivalent
    supported production injection path.
    """
    path = Path(repo) / "hermes_cli" / "kanban_db.py"
    original = path.read_text(encoding="utf-8")
    text = original

    replacements = [
        (
'''    def _any_spawnable_review() -> bool:\n        if not review_rows:\n            return False\n        try:\n''',
'''    def _any_spawnable_review() -> bool:\n        if not review_rows:\n            return False\n        # Experimental external-spawn seam: when the caller supplied a\n        # spawn_fn, that function owns assignee realization. A non-profile\n        # lane can therefore be spawnable without becoming a fake profile.\n        if spawn_fn is not None:\n            return any(row["assignee"] for row in review_rows)\n        try:\n''',
        ),
        (
'''    if _default_assignee:\n        try:\n            from hermes_cli.profiles import profile_exists as _pe\n            _default_assignee_resolved = bool(_pe(_default_assignee))\n        except Exception:\n            # Profiles module not importable (test stubs, exotic envs).\n            # Trust the operator's config and try the assignment; the\n            # downstream profile_exists check on the assigned row will\n            # bucket it as nonspawnable if the profile genuinely isn't\n            # there, with the existing diagnostic.\n            _default_assignee_resolved = True\n''',
'''    if _default_assignee:\n        if spawn_fn is not None:\n            _default_assignee_resolved = True\n        else:\n            try:\n                from hermes_cli.profiles import profile_exists as _pe\n                _default_assignee_resolved = bool(_pe(_default_assignee))\n            except Exception:\n                # Profiles module not importable (test stubs, exotic envs).\n                # Trust the operator's config and try the assignment; the\n                # downstream profile_exists check on the assigned row will\n                # bucket it as nonspawnable if the profile genuinely isn't\n                # there, with the existing diagnostic.\n                _default_assignee_resolved = True\n''',
        ),
        (
'''        if profile_exists is not None and not profile_exists(row_assignee):\n''',
'''        if spawn_fn is None and profile_exists is not None and not profile_exists(row_assignee):\n''',
        ),
        (
'''        if profile_exists is not None and not profile_exists(row["assignee"]):\n''',
'''        if spawn_fn is None and profile_exists is not None and not profile_exists(row["assignee"]):\n''',
        ),
    ]

    # The two profile gates may occur in multiple copies in generated/source text;
    # exactly one ready gate and one review gate are expected in current main.
    for old, new in replacements[:2]:
        if new in text:
            continue
        count = text.count(old)
        if count != 1:
            raise UpstreamDriftError(f"expected exactly one upstream seam, found {count}: {old.splitlines()[0]}")
        text = text.replace(old, new, 1)

    for old, new in replacements[2:]:
        if new in text:
            continue
        count = text.count(old)
        if count != 1:
            raise UpstreamDriftError(
                f"expected exactly one upstream profile gate, found {count}: {old.strip()}"
            )
        text = text.replace(old, new, 1)

    before = _sha(original)
    after = _sha(text)
    changed = text != original
    if write and changed:
        path.write_text(text, encoding="utf-8")
    return PatchResult(changed, before, after, path)
