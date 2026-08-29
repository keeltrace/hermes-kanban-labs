# Security

Hermes Kanban Labs executes agent workloads on remote machines. Treat worker hosts, transferred workspaces, and model endpoints as privileged infrastructure.

## Authority boundaries

- No `kanban.db` is shared over the network.
- Labs creates no task database or scheduler.
- Controller task state remains upstream Hermes SQLite.
- TOML is execution/policy configuration only.
- Completion is fenced by upstream `expected_run_id`.
- Heartbeats use the exact upstream `claim_lock`.
- Lost claim => remote cancellation + no stale completion.
- Remote non-zero exit is never silently converted into success.

## Git workspace transport

`workspace="git"` intentionally transfers Git history reachable from the task's base `HEAD` to the remote worker host through a Git bundle, plus dirty/untracked workspace files through rsync. Do not use a worker host that is not trusted to receive that repository history and task workspace.

The transport does **not** copy GitHub/GitLab origin credentials. Remote Git results are fetched into a dedicated `refs/hermes-kanban-labs/results/...` ref; Labs does not automatically merge/reset the user's current branch.

Git mode requires the upstream card workspace to be a real `worktree`; this fails closed rather than widening a normal/shared repository directory into a remote coding workspace.

## SSH

Use normal SSH host-key verification. Do not add `StrictHostKeyChecking=no` to examples or automation. Prefer a private LAN, VPN, or tailnet.

## Docker

Labs assumes a trusted Docker-capable worker host. Docker daemon access is privileged on typical installations. Do not expose the Docker daemon TCP socket publicly and do not mount the controller's Docker socket into task containers by default.

## Secrets

Controller credential directories are not copied to workers. If an API credential is needed, create an env file directly on the worker and reference it with `remote_env_file`.

## Frontier / destructive behavior

Frontier budgets are currently advisory/diagnostic rather than an upstream hard create gate. Do not grant autonomous agents broad destructive board-management permissions as a substitute for growth control. Preserve board history; fix excess work through completion, merging, archival, or explicit blocking.

## Experimental code

This is alpha software tracking a fast-moving upstream. Review the compatibility patch on every upstream sync and run the smoke/test suite before deploying new commits.
