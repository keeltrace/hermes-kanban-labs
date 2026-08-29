# Hermes Kanban Labs

**A fast-moving experimental Kanban integration branch for [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) power users.**

Labs stays close to Hermes `main`, composes promising upstream PRs/issues, and makes advanced Kanban worker patterns usable **now** without creating a competing board, scheduler, or state system.

> **Hermes owns the board. Labs adds policy and experimental execution backends.**

## v0.2: the three-plane model

```text
STATE — upstream Hermes SQLite (only authority)
  tasks / links / runs / comments / review / retry

POLICY — Labs TOML
  board -> workflow -> nested path -> card
  prompts / model defaults / frontier budgets

EXECUTION
  local profile | SSH+Docker worker | one sharded-model superworker
```

A remote worker is now intended to be **as expressive as a local Hermes worker**: native card model/provider/reasoning/skills flow across the SSH boundary, and Git workspaces preserve a real worktree rather than flattening `.git` away.

## What it unlocks

```text
                         MAIN HERMES
                    canonical Kanban
                           │
             claim / run / retry / review
                           │
                 Labs spawn adapter
            ┌──────────────┴──────────────┐
            │                             │
      remote standalone              cluster worker
      logical worker #1             logical worker #2
            │                             │
      SSH -> Docker Hermes           SSH -> Docker Hermes
            │                             │
       whole model/API               ONE inference endpoint
                                          │
                                  distributed model backend
                                  Mac1 ... Mac20 / GPUs / etc.
```

To Kanban, a 20-Mac model cluster is **one worker**. The model-stage machines are inference infrastructure, not twenty board workers.

## What changed in v0.2

### Git-native remote execution

Set:

```toml
workspace = "git"
```

Labs now:

1. validates the resolved Hermes workspace is a Git worktree;
2. bundles the exact local `HEAD` without sending origin credentials;
3. creates/reuses a remote bare cache and a run-specific worktree;
4. overlays dirty/untracked files while preserving remote `.git` state;
5. runs Dockerized Hermes in that worktree;
6. syncs files back;
7. fetches the remote commit into:

```text
refs/hermes-kanban-labs/results/<task-run>
```

It never silently resets or moves your controller branch. Inspect/diff/cherry-pick/merge the result ref yourself or through your agent workflow.

This remote transport intentionally complements upstream PR **#91981** instead of rebuilding its task-scoped Docker worktree authority.

### Adaptive workflow policy

TOML is now a policy layer with deterministic precedence:

```text
worker defaults
 -> global
 -> board
 -> workflow
 -> matching nested board paths
 -> matching nested workflow paths
 -> native Hermes card overrides
```

Example:

```toml
[boards.default.workflows.release]
prompt = "Produce reviewable release slices."

[boards.default.workflows.release.paths."research"]
model = "fast-model"

[boards.default.workflows.release.paths."research.deep"]
model = "strong-model"
reasoning_effort = "high"

[boards.default.workflows.release.paths."implementation"]
model = "coding-model"
```

A card at `research.deep.compare` inherits `research` then `research.deep`. Native Hermes `model_override`, `provider_override`, `reasoning_effort`, and card skills win last.

### Anti-sprawl frontier budgets

```toml
[policy]
max_open_cards = 30
max_ready_cards = 8
max_children_per_card = 5
max_depth = 5
```

Inspect the live canonical board:

```bash
hkl --config ~/.config/hermes-kanban-labs/workers.toml \
  frontier --board default
```

When open/ready budgets are saturated, the policy says **finish, merge, archive, or explicitly block existing work before expanding the graph**. Deleting board history is never a pressure-relief strategy.

v0.2 intentionally does not patch upstream `kanban_create` yet; there is no clean pre-create policy seam on current main, and widening the Labs patch into canonical mutation ownership would violate the project's own boundary. See `docs/ANTI_SPRAWL.md`.

### Vertical workflow/path view

```bash
hkl tree --board default
hkl tree --board default --json
```

This projects upstream `workflow_template_id` + nested `current_step_key` vertically while keeping actual `task_links` dependencies visible separately.

Labs does **not** create another board API. Upstream's Kanban/dashboard API remains canonical; `--json` is a Labs projection for scripts and future plugin UI work.

## Why this repo exists

Relevant upstream destinations include:

- [#29244 — Distributed Kanban workers with central board visibility](https://github.com/NousResearch/hermes-agent/issues/29244)
- [#70547 — production path for the existing `spawn_fn` seam](https://github.com/NousResearch/hermes-agent/issues/70547)
- [#94363 — Hermes Mesh RFC / edge-compute fabric](https://github.com/NousResearch/hermes-agent/issues/94363)
- [#91981 — task-scoped Docker worktrees](https://github.com/NousResearch/hermes-agent/pull/91981)

Labs is a proving ground for compositions of that work. As equivalent features land upstream, the desired outcome is to **delete Labs compatibility code**.

## Non-negotiable boundary

Labs does **not** own:

- another task database;
- another scheduler;
- dependency truth;
- retry/failure accounting;
- completion/review authority;
- a replacement for `kanban.db`;
- model-shard placement inside a distributed inference engine.

## Install

From a Hermes source checkout/fork:

```bash
python -m pip install --no-deps -e /path/to/hermes-kanban-labs
python /path/to/hermes-kanban-labs/scripts/apply_upstream_patch.py /path/to/hermes-agent
```

The compatibility patch only makes the existing `spawn_fn` seam reachable for non-profile assignees when a custom spawner is explicitly supplied. Normal `spawn_fn=None` behavior remains upstream behavior.

Configure:

```bash
mkdir -p ~/.config/hermes-kanban-labs
cp examples/workers.toml ~/.config/hermes-kanban-labs/workers.toml
$EDITOR ~/.config/hermes-kanban-labs/workers.toml
```

Verify workers:

```bash
hkl --config ~/.config/hermes-kanban-labs/workers.toml doctor --pull
```

Run the experimental dispatcher:

```bash
hkl --config ~/.config/hermes-kanban-labs/workers.toml dispatch
```

Assign normal Hermes cards to configured Labs worker names. Ordinary profile assignees still fall through to upstream `_default_spawn`.

## Failure behavior

```text
remote exits 0
  -> exact-run fenced completion

remote exits nonzero
  -> local bridge exits nonzero
  -> upstream crash/retry/breaker owns recovery

claim lost
  -> remote execution canceled
  -> stale bridge forbidden from completing successor run

Git result captured
  -> fetched into result ref
  -> controller branch is not silently modified
```

## Smoke test

```bash
./scripts/smoke.sh
```

The suite covers policy precedence, nested paths, card override fidelity, Git bundle transport, vertical tree projection, frontier saturation, claim loss, remote exit failure, exact-run completion, no-second-authority checks, patch idempotence, and the subprocess bridge/SSH/Docker command path.

## Staying near `main`

`scripts/sync_upstream.sh` refuses dirty trees, rebases onto NousResearch `main`, reapplies the tiny compatibility seam, and stops for review. It never force-pushes automatically. CI also checks the seam for upstream drift.

Current v0.2 development pin is recorded in `UPSTREAM_PIN`; do not interpret that as a promise that fast-moving upstream has stopped changing.

## Status

**Experimental alpha / power users.** v0.2 materially improves Git/workflow parity and board legibility, but a real external SSH/Docker machine and real sharded inference cluster are still required for `FINISHED_FOR_REAL` hardware evidence.

Read next:

- `docs/ARCHITECTURE.md`
- `docs/WORKFLOW_POLICY.md`
- `docs/GIT_REMOTE_WORKSPACES.md`
- `docs/ANTI_SPRAWL.md`
- `SURGE_REPORT.md`
