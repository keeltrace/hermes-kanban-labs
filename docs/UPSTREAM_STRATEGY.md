# Upstream strategy

Hermes Kanban Labs is a fast-moving experimental downstream, not a permanent fork ideology.

## Rules

1. Track `NousResearch/hermes-agent/main` closely.
2. Prefer upstream primitives over Labs abstractions.
3. Carry the smallest possible compatibility patch.
4. Delete local code when upstream gains an equivalent supported capability.
5. Link experiments to relevant upstream issues and share concrete failure evidence.
6. Do not pressure upstream maintainers to merge an experiment merely because Labs ships it.
7. Never conceal a fork-only behavior as an upstream Hermes capability.

## Current seam

The only upstream source patch in v0.1 is the non-profile custom-`spawn_fn` gate in `hermes_cli/kanban_db.py`.

Its deletion condition is simple: once upstream provides a supported way for external/non-profile workers to use the dispatcher lifecycle, remove the patch and adapt Labs to that interface.

## Daily drift

`.github/workflows/upstream-main.yml` checks out current upstream main, applies the seam, parses the resulting file, and verifies that:

- `dispatch_once` still exposes `spawn_fn`;
- `_default_spawn` still exists for mixed mode;
- `heartbeat_claim` still supports a caller-supplied claimer;
- `complete_task` still supports `expected_run_id` fencing;
- the Labs gate is present after patching.

A drift failure is a review signal, not an invitation to automatically rewrite upstream code.
