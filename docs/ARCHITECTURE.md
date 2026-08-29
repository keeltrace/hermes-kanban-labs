# Architecture

## Three planes, one authority

```text
STATE PLANE — upstream Hermes only
  kanban.db
  tasks / task_links / runs / comments / lifecycle / review / retries

POLICY PLANE — Hermes Kanban Labs TOML
  worker realization
  board/workflow/path prompts
  model/provider/reasoning defaults
  frontier budgets

EXECUTION PLANE
  upstream local profiles
  SSH + Docker workers
  sharded/distributed inference behind one logical worker
```

TOML never mirrors task state and Labs never creates another scheduler or task ledger.

## Experimental spawn seam

Current upstream `dispatch_once()` accepts `spawn_fn(task, workspace_path, board) -> Optional[int]`, but profile gates skip non-profile assignees before a custom function can realize them. Labs carries a tiny compatibility patch that bypasses those profile-only checks only when `spawn_fn` is explicitly supplied.

```text
spawn_fn=None -> real Hermes profile -> upstream _default_spawn
spawn_fn=Labs -> Labs worker name -> local bridge -> experimental executor
              -> ordinary profile -> upstream _default_spawn
```

## Local bridge = lifecycle compatibility

Upstream expects a host-local PID. Labs returns a disposable local bridge PID even when work runs elsewhere. The bridge heartbeats the exact upstream claim, cancels remote execution if ownership is lost, and completes only the exact `current_run_id` it was given.

Remote nonzero exit is not translated into success or a Labs retry. The bridge exits nonzero and upstream Hermes remains responsible for crash detection, retry, and failure-breaker behavior.

## Adaptive execution policy

Execution policy resolves from broad to narrow:

`worker -> global -> board -> workflow -> nested path -> native card override`

Prompts stack; model/provider/reasoning override. Native card `model_override`, `provider_override`, `reasoning_effort`, and `skills` win last. See `WORKFLOW_POLICY.md`.

## Git-native remote workspace

`workspace="git"` creates a run-specific Git worktree on the SSH host from a credential-free bundle of the exact controller HEAD. Dirty/untracked files are overlaid without replacing `.git`. After execution, the remote commit is fetched back into a Labs result ref; Labs never silently moves the controller's branch. See `GIT_REMOTE_WORKSPACES.md`.

Upstream PR #91981 owns task-scoped Docker worktree authority inside Hermes. Labs tracks/reuses that work rather than competing with it.

## Sharded cluster worker

```text
upstream card
 -> ONE Labs bridge PID
 -> SSH coordinator
 -> ONE Dockerized Hermes agent
 -> one inference endpoint
 -> distributed model backend (Shard / MLX / other)
      node 1 ... node N
 -> one result
 -> exact upstream completion
```

The inference nodes are not Kanban workers. Labs does not own tensor/model placement.

## Vertical/tree projection

`hkl tree --board <slug>` reads the canonical Hermes task/link state and renders cards vertically by `workflow_template_id` and nested `current_step_key`. Dependency parents/children remain explicit metadata; path nesting is not silently reinterpreted as dependency state.

`--json` exposes the same projection for scripts without introducing an HTTP service or second API authority. The upstream Kanban dashboard API remains the board/card API.

## Frontier budgets

`hkl frontier` reads canonical state and applies policy-plane limits. This release deliberately stops short of patching upstream card creation; see `ANTI_SPRAWL.md` for the ownership boundary.
