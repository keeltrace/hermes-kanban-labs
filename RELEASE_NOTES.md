# Hermes Kanban Labs v0.2.0 — SURGE update

v0.2 is a direct response to community review of the first public alpha.

## Major changes

- **Git-native SSH workers:** `workspace="git"` preserves a real remote worktree, overlays dirty/untracked files, and fetches remote commits back into a non-destructive local result ref.
- **Adaptive policy:** board, workflow, nested path, and prompt/model/reasoning policy in TOML; native Hermes card overrides remain final authority.
- **Remote semantic parity:** per-card model, provider, reasoning effort, and skills now reach the Dockerized remote Hermes invocation.
- **Vertical tree projection:** `hkl tree` renders workflow/path nesting while preserving parent-child dependency metadata.
- **Frontier budgets:** `hkl frontier` projects open/ready saturation from the canonical Hermes DB and provides anti-sprawl operating limits.
- **Clear state boundary:** SQLite is still upstream Hermes' only board authority; TOML is policy/config only.

## Deliberately not implemented

- no second scheduler or task DB;
- no Labs-owned board REST service;
- no fake Shard cluster-formation API;
- no autonomous hard patch to upstream `kanban_create` until there is a clean admission-policy seam;
- no silent branch merge/reset after remote Git execution.

## Upstream composition

The Git transport is designed to complement, not duplicate, open upstream PR #91981 (task-scoped Docker worktree authority). The external worker compatibility seam remains temporary pending an upstream-supported equivalent of #70547.

## Evidence

Run `./scripts/smoke.sh`. The release records the exact test count and packaging checks in `evidence/` at build time.
