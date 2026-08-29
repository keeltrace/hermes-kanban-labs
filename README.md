# Hermes Kanban Labs

**Experimental power-user Kanban workers for [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).**

Hermes Kanban Labs exists to make advanced Kanban worker patterns usable **now**, while upstream APIs are still being designed and merged. It is intentionally a thin experimental layer, not a competing agent framework and not a second Kanban implementation.

> **One Hermes board remains authoritative. Labs changes how a claimed worker is launched.**

## What it unlocks

A normal Hermes host can keep using its native Kanban board, dashboard, dependencies, claims, run IDs, retry/failure breaker, review lane, concurrency controls, and worker logs while some assignees execute somewhere else.

```text
                         MAIN HERMES
                  canonical Kanban board
                           │
             claim / run / retry / review
                           │
              experimental spawn seam
                  ┌────────┴────────┐
                  │                 │
                  ▼                 ▼
          standalone worker     cluster worker
          one remote box        one logical worker
                  │                 │
          Dockerized Hermes     Dockerized Hermes
                  │                 │
             whole model       one inference endpoint
                                    │
                             sharded model backend
                         Mac1 ─ Mac2 ─ ... ─ Mac20
```

To Kanban, `monster-shard` is **one worker**. The twenty model-stage machines beneath its inference endpoint are not twenty Kanban workers.

## Why this repo exists

Upstream already has the right primitives and active design work:

- [#29244 — Distributed Kanban workers with central board visibility](https://github.com/NousResearch/hermes-agent/issues/29244)
- [#70547 — production path for the existing `spawn_fn` seam](https://github.com/NousResearch/hermes-agent/issues/70547)
- [#94363 — Hermes Mesh RFC / edge-compute fabric](https://github.com/NousResearch/hermes-agent/issues/94363)

Labs does not wait for those designs to settle before power users can experiment. It stays deliberately close to `main`, proves a narrow integration, and should **delete local compatibility patches as upstream absorbs them**.

## Non-negotiable architecture rule

Labs does **not** own:

- a second task database;
- a second task scheduler;
- task dependencies;
- retries or failure counting;
- Kanban completion authority;
- review state;
- a distributed replacement for `kanban.db`.

Those remain upstream Hermes responsibilities.

Labs owns only the execution adapter between an upstream claimed run and an experimental worker backend.

## Current alpha

Verified against upstream commit:

```text
3f36c87e1ebdfbf7d14a88229dc9be222c12ea89
```

Current implementation:

- mixed local + experimental lanes on the same normal Hermes board;
- remote SSH + Docker Hermes workers;
- official `nousresearch/hermes-agent` image;
- optional `rsync` task workspace transfer;
- local bridge PID returned to upstream, preserving upstream crash detection;
- claim heartbeats use the upstream `claim_lock`;
- completion is fenced by upstream `expected_run_id`;
- lost ownership cancels the remote worker and refuses stale completion;
- non-zero remote exit is left to upstream crash/retry/failure-breaker logic;
- a `shard_cluster` worker points one Hermes agent at one distributed inference gateway;
- no custom persistent control service is required on remote machines.

## Installation — power-user source checkout

Start from a current Hermes source checkout/fork. Labs is intentionally optimized for people already tracking Hermes `main`.

```bash
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent

# Clone Hermes Kanban Labs next to it after publishing this repository.
# git clone https://github.com/<owner>/hermes-kanban-labs.git ../hermes-kanban-labs

python -m pip install --no-deps -e ../hermes-kanban-labs
python ../hermes-kanban-labs/scripts/apply_upstream_patch.py .
```

Review the tiny change to `hermes_cli/kanban_db.py`, then run your normal Hermes test/install process. The patch only changes profile-gating behavior when a caller explicitly supplies `spawn_fn`; stock `spawn_fn=None` behavior is preserved.

## Configure workers

```bash
mkdir -p ~/.config/hermes-kanban-labs
cp ../hermes-kanban-labs/examples/workers.toml \
  ~/.config/hermes-kanban-labs/workers.toml
$EDITOR ~/.config/hermes-kanban-labs/workers.toml
```

A standalone worker:

```toml
[workers.mac-mini-01]
backend = "ssh-docker"
ssh = "you@mac-mini-01.local"
provider = "openai-api"
model = "your-local-model"
base_url = "http://host.docker.internal:8080/v1"
workspace = "rsync"
```

A sharded superworker:

```toml
[workers.monster-shard]
kind = "shard_cluster"
cluster_nodes = 20
backend = "ssh-docker"
ssh = "you@cluster-coordinator.local"
provider = "openai-api"
model = "huge-distributed-model"
base_url = "http://10.0.0.50:8000/v1"
workspace = "rsync"
```

Labs does not care whether that endpoint is backed by Shard, MLX distributed inference, another engine, or one enormous server. For the MVP, the contract is simply an inference endpoint that the Dockerized Hermes worker can use.

## Worker setup

There is deliberately no Hermes installation ceremony on every worker machine. A worker host needs SSH and Docker. Model serving is operator-owned.

```bash
hkl --config ~/.config/hermes-kanban-labs/workers.toml doctor --pull
```

`--pull` verifies Docker and pulls the configured Hermes image.

Credentials are not copied from the controller. If a worker needs provider secrets, place an env file on that worker yourself and set an **absolute** `remote_env_file` path in its config.

## Run the experimental dispatcher

```bash
hkl --config ~/.config/hermes-kanban-labs/workers.toml dispatch
```

Assign cards to worker names using ordinary Hermes Kanban operations:

```text
assignee = mac-mini-01
assignee = monster-shard
```

Ordinary Hermes profile assignees still route through upstream `_default_spawn`. Experimental assignees route through the Labs bridge.

The stock gateway dispatcher can remain active. With `spawn_fn=None` it continues to skip non-profile lanes, while the Labs dispatcher can claim those lanes using the custom spawner. Hermes' existing dispatch lock / atomic claim behavior remains the authority.

## How failure behaves

Labs intentionally avoids clever fallback:

```text
remote worker exits 0
    -> complete exact current run

remote worker exits nonzero
    -> bridge exits nonzero
    -> card remains under upstream lifecycle
    -> upstream crash detection / retry / breaker handles it

claim heartbeat fails
    -> cancel remote worker
    -> refuse completion
    -> stale bridge cannot mutate successor run
```

That behavior is tested.

## Smoke test

```bash
./scripts/smoke.sh
```

The release smoke includes unit tests, failure injection, upstream-patch drift checks, and a real subprocess path using disposable `ssh` and `docker` command shims:

```text
bridge -> ssh subprocess -> docker command shim -> worker output -> exact-run completion
```

This proves the process/protocol path without pretending this build environment had a real remote Docker host. Before relying on a machine, run `hkl ... doctor --pull` and one disposable card against your actual hardware.

## Staying close to upstream

For a Hermes fork, `scripts/sync_upstream.sh` performs a conservative local sync:

1. require a clean working tree;
2. fetch `NousResearch/hermes-agent main`;
3. rebase onto upstream main;
4. re-apply the tiny Labs compatibility seam;
5. stop for human diff/test review;
6. never force-push automatically.

A scheduled GitHub Actions workflow also checks current upstream `main` for seam drift. If upstream lands #70547-equivalent functionality, the desired response is to remove our patch, not fight upstream.

## Status

**Experimental alpha / power users.** The code path is smoke-tested and fail-closed, but the packaged release has not been live-smoked against your specific SSH/Docker/model hardware. That is intentionally stated rather than hidden.

See [SURGE_REPORT.md](SURGE_REPORT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [SECURITY.md](SECURITY.md).
