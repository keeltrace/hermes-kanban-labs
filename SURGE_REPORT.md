# SURGE convergence report

## CURRENT STATE

The starting `Hermes Fleet v0.2` ZIP had useful SSH/Docker worker code but also introduced a separate FastAPI control plane, SQLite task store, and scheduler. That architecture duplicated the authority Hermes Kanban already owns.

Upstream reality on 2026-08-29:

- Hermes Kanban already owns a shared SQLite board, CAS claims, task runs, dependencies, retry/failure breaker, review dispatch, concurrency controls, worker PIDs, logs, and heartbeats.
- `dispatch_once(..., spawn_fn=...)` already exists.
- Current profile gates prevent that seam from realizing non-profile lanes in production.
- #29244 tracks distributed workers with one central board.
- #70547 tracks a supported production path for the existing external spawn seam.
- #94363 tracks broader mesh/edge-compute composition.

## TARGET STATE

A publishable experimental Hermes power-user release that stays close to upstream `main` and makes extreme Kanban subworkers usable now:

- one canonical Hermes control/board;
- unlimited logical worker definitions subject to upstream concurrency;
- standalone remote Dockerized Hermes workers;
- one logical worker optionally backed by many model-shard machines;
- no duplicate board, scheduler, retry engine, or lifecycle authority;
- explicit fail-closed run fencing;
- reproducible smoke evidence;
- current-main drift detection.

## DUPLICATES KILLED

- Labs/Fleet SQLite `tasks` database: removed.
- Labs scheduler: removed.
- persistent node-agent/control WebSocket plane: removed from the critical path.
- custom retry/completion ledger: removed.
- model-shard scheduling inside Kanban: rejected; that belongs to the inference backend.

## ACTIVE OWNERS TO RESPECT

- NousResearch/hermes-agent maintainers own canonical Kanban semantics.
- Upstream #29244 / #70547 / #94363 own relevant design destinations.
- Model-sharding projects own tensor/model placement; Labs consumes an inference endpoint.

## CLEAN GAPS

1. Make the already-existing `spawn_fn` seam usable for non-profile lanes without changing stock behavior.
2. Map one experimental assignee to one local bridge PID.
3. Let that bridge execute Hermes remotely through SSH/Docker.
4. Preserve upstream heartbeat/crash/run fencing.
5. Treat a sharded inference cluster as one logical worker endpoint.
6. Continuously test against current upstream main.

## ROOK

**Score: 9.2/10. Hard veto: cleared after redesign.**

Required corrections completed:

- removed second source of truth;
- kept compatibility patch minimal and deletable;
- preserved upstream default spawn for normal profiles;
- stale run cannot complete successor run;
- remote failure is visible and handed to upstream retry logic;
- no silent credential copying;
- sync script refuses dirty-tree automation and never force-pushes.

Remaining ROOK debt: the compatibility patch touches a private-ish upstream seam and therefore needs continuous drift testing until upstream exposes a supported production hook.

## NOVA

**Score: 9.0/10.**

The user journey is now the intended one: main Hermes keeps normal Kanban; power users configure remote worker names; one worker can be an ordinary machine or a distributed-model superworker; no Hermes install is required on every executor beyond Docker image execution.

Remaining NOVA debt: this build environment had no Docker daemon or external SSH host, so the packaged alpha cannot truthfully claim a live physical-hardware run here.

## SURGE

**Score: 9.6/10.**

Work was converted from architecture discussion into code, failure injection, process smoke, current-main compatibility checks, CI, sync tooling, and a publishable artifact. Upstream open issues were treated as destinations rather than reasons to wait.

## WINNING ACTION

Ship the thin experimental execution layer and tiny current-main compatibility seam now; delete pieces as upstream absorbs them.

## PARALLEL ACTION

Community contributors can add/test executor backends, Mac/Apple Silicon model gateways, workspace transports, observability, and real hardware matrices without changing the canonical Kanban authority.

## COLLABORATION ACTION

Feed concrete integration findings back to #29244/#70547 and consume upstream changes as soon as equivalent seams land.

## TRUE BLOCKER

No architectural blocker remains for publishing the experimental alpha. A true live hardware acceptance run requires an actual Docker-capable SSH worker/model endpoint; this sandbox did not provide one.

## NEXT EXECUTABLE STEP

Publish the repository as an experimental alpha, then run `hkl ... doctor --pull` and one disposable real Kanban task on a community test machine. Record that matrix in the first release notes rather than rewriting architecture again.

## EVIDENCE PRODUCED

- 17/17 Python tests passing during convergence.
- real subprocess smoke: bridge -> SSH shim -> Docker command shim -> worker output -> exact-run completion.
- paired remote-exit failure smoke proving no false completion.
- lost-claim failure injection proving cancellation and no stale completion.
- patch idempotence + upstream-drift failure tests.
- no-second-authority guard.
- Python compilation and CLI smoke.
- isolated `pip --target` package install and wheel build succeeded.

## ARTIFACTS PRODUCED

- working `hermes_kanban_labs` package;
- conservative upstream patcher;
- SSH/Docker executor;
- sharded-worker configuration contract;
- upstream sync tooling;
- scheduled current-main compatibility workflow;
- architecture/security/contribution docs;
- publishable ZIP + checksums.

## STATUS

**FINISHED** — publishable experimental alpha. Not labeled `FINISHED_FOR_REAL` until a real external Docker host/model endpoint completes the physical hardware acceptance run.
