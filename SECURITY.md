# Security

Hermes Kanban Labs executes agent workloads on remote machines. Treat worker hosts and model endpoints as privileged infrastructure.

## Defaults and boundaries

- No `kanban.db` is shared over the network.
- No Labs task database exists.
- No controller credential directory is copied to workers.
- Remote worker provider secrets, if needed, live in an operator-created env file on that remote host.
- Task completion is fenced by upstream `expected_run_id`.
- Heartbeats use the exact upstream `claim_lock`.
- Lost claim => remote cancellation + no completion.
- Remote non-zero exit is not silently converted into success.

## SSH

Use normal SSH host-key verification. Do not add `StrictHostKeyChecking=no` to examples or automation. Prefer a private LAN, VPN, or tailnet.

## Docker

Labs currently assumes a trusted Docker-capable worker host. Membership in a Docker group is effectively privileged on typical Linux installations. Do not expose the Docker daemon TCP socket publicly.

## Secrets

Prefer local inference endpoints when possible. If an API credential is needed, create an env file directly on the worker and reference an absolute path with `remote_env_file`. Labs does not provision or synchronize that file.

## Experimental code

This is alpha software tracking a fast-moving upstream. Review the compatibility patch on every upstream sync and run the smoke/test suite before deploying new commits.
