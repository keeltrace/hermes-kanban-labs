# Frontier budgets: containing Kanban sprawl

Execution concurrency and graph growth are different problems.
`max_in_progress` stops too many workers from running; it does not stop an orchestrator from creating fifty speculative cards.

Labs v0.2 adds **frontier budgets** to the policy plane:

```toml
[policy]
max_open_cards = 30
max_ready_cards = 8
max_children_per_card = 5
max_depth = 5
```

The dispatcher snapshots the canonical board and injects the current frontier state into experimental worker context. `hkl frontier` gives humans/scripts the same projection and exits nonzero when the configured open/ready frontier is saturated.

When saturated, the operating rule is:

> Do not expand the graph. Finish, merge, archive, or explicitly block existing work first.

Deletion is not a pressure-relief strategy. Board history is evidence and should not be erased merely because an agent created too much work.

## v0.2 boundary

The budget projection is real and tested, but Labs does **not** patch upstream `kanban_create` yet. That would widen the compatibility patch from the external-spawn seam into canonical board mutation policy without an upstream pre-create extension hook. ROOK rejects that ownership jump for this release.

The next clean upstream-facing seam is an admission/policy hook around card creation. Until then, use the frontier command as a CI/operator gate and keep `auto_promote_children=false` on boards where decomposition needs human control.
