# Architecture

## Authority

There is one authority: upstream Hermes Kanban.

`hermes_cli.kanban_db` owns tasks, dependencies, claims, runs, retries, completion, review, logs, and dispatch concurrency. Hermes Kanban Labs must never become another owner of those facts.

## Experimental seam

Current upstream `dispatch_once()` already accepts `spawn_fn(task, workspace_path, board) -> Optional[int]`, but current profile gates skip non-profile assignees before the custom function is reached. Labs carries a deliberately small compatibility patch that bypasses those profile-only checks **only when `spawn_fn` is explicitly supplied**.

That means the stock path remains stock:

```text
spawn_fn=None -> require real Hermes profile -> upstream _default_spawn
```

Labs path:

```text
spawn_fn=Labs -> assigned lane may be external -> Labs decides realization
```

## Mixed mode

The Labs spawner receives every task the patched dispatcher is allowed to spawn.

- configured Labs worker name -> launch local bridge;
- anything else -> call upstream `_default_spawn` unchanged.

This lets one board contain normal local profiles and experimental remote workers.

## Why the bridge is local

Upstream stores a worker PID and uses host-local process liveness as part of its lifecycle safety net. Labs therefore launches a small **local bridge process** and returns that PID to upstream.

The bridge owns only:

- remote process transport;
- upstream claim heartbeat on behalf of the remote execution;
- exact-run completion after a successful result;
- cancellation of remote work if ownership is lost.

The bridge is disposable and stores no task ledger.

## Standalone worker

```text
upstream card
 -> Labs local bridge PID
 -> SSH
 -> Docker
 -> official Hermes image
 -> whole model or ordinary provider
 -> result
 -> exact upstream run completion
```

## Sharded cluster worker

```text
upstream card
 -> ONE Labs local bridge PID
 -> SSH coordinator
 -> ONE Dockerized Hermes agent
 -> OpenAI-compatible inference endpoint
 -> distributed model system
      shard node 1
      shard node 2
      ...
      shard node N
 -> one agent result
 -> exact upstream run completion
```

The model-shard machines are inference infrastructure, not Kanban workers. Labs intentionally does not own their scheduling.

## Workspace MVP

`workspace="none"` transfers no host workspace.

`workspace="rsync"` copies the claimed workspace to a run-specific directory on the remote host, excluding `.git/`, mounts it into the Hermes container as `/workspace`, then syncs modifications back after successful process exit. A sync-back failure turns the execution into a failure instead of silently claiming success.

This is not yet a full git-worktree transport. That is future work and should reuse upstream worktree semantics rather than inventing a second branch manager.
