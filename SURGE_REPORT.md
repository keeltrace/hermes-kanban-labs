# BIG BROTHER 3.3 + SURGE convergence report — v0.2.0

## GOAL

Turn the first public alpha into a genuinely useful **Kanban Labs** release: stay near upstream Hermes `main`, preserve the canonical board/lifecycle, and make experimental remote workers inherit the same Git and per-card execution semantics power users expect locally.

## USER JOURNEY

A power user should be able to:

1. keep one normal Hermes Kanban board as authority;
2. assign cards to local profiles, SSH/Docker workers, or one logical worker backed by a distributed model cluster;
3. define different prompts/models/reasoning by board, workflow, and nested path while retaining card-level overrides;
4. let remote coding workers operate in real Git worktrees and return inspectable commits;
5. view workflow/path structure vertically without losing dependency relationships;
6. see when the board frontier is too large and stop speculative expansion before agents cope by destroying history.

## ACCEPTANCE CONDITIONS

- No second board DB, scheduler, retry ledger, or completion authority.
- Remote execution preserves card model/provider/reasoning/skills.
- Git transport preserves real worktree semantics and never silently moves the controller branch.
- TOML is policy only; SQLite remains state.
- Workflow/path policy is deterministic and nested.
- Vertical projection reads canonical state and can emit JSON.
- Frontier budget projection is derived from canonical state and never mutates it.
- Current upstream-owned work is reused instead of cloned into Labs.
- Tests exercise policy precedence, Git movement, lifecycle fencing, and failure behavior.

## NON-GOALS

- Replacing the Hermes dashboard/API.
- Creating a Labs workflow database.
- Implementing tensor/model sharding itself.
- Auto-merging remote Git results.
- Taking ownership of upstream card creation without a clean policy/admission seam.

---

## CURRENT STATE

v0.1 correctly removed the earlier duplicate Fleet control plane, but community review exposed four material gaps:

- SSH workspace transfer stripped `.git`, making remote coding workers less capable than local worktree workers.
- Worker TOML model/provider defaults could override/drop richer native per-card execution intent.
- TOML versus SQLite authority was not explained clearly enough.
- There was no good projection for workflow paths or a direct answer to graph/card sprawl.

## TARGET STATE

v0.2 uses three explicit planes:

```text
STATE      upstream Hermes SQLite only
POLICY     Labs TOML (worker / board / workflow / nested path / budgets)
EXECUTION  local / SSH+Docker / distributed inference endpoint
```

## DUPLICATES KILLED

- **New Git-worktree manager:** killed. Upstream PR #91981 already owns task-scoped Docker/worktree authority. Labs adds only remote-host transport around the concept.
- **New board REST API:** killed. Upstream dashboard/plugin APIs remain canonical. Labs exposes projections through CLI/JSON.
- **New workflow state store:** killed. Existing Hermes `workflow_template_id` and `current_step_key` are reused.
- **New task scheduler / retry engine:** still killed from v0.1. Upstream dispatch/claims/runs/breaker remain authoritative.
- **Hard patch into `kanban_create`:** rejected for v0.2. No clean pre-create policy seam exists on the current integration boundary; widening the patch would create mutation-policy ownership Labs should not silently assume.

## ACTIVE OWNERS TO RESPECT

- Hermes maintainers own canonical Kanban state/lifecycle/API semantics.
- #70547 owns the destination for a production external-spawn seam.
- #29244 owns the central-board distributed-worker direction.
- #91981 actively owns task-scoped Docker/worktree authority.
- Distributed inference projects own model/tensor placement.

## CLEAN GAPS ACTUALIZED

1. Remote Git transport around a real task worktree.
2. Execution-policy parity for card model/provider/reasoning/skills.
3. Board/workflow/nested-path policy composition.
4. Vertical workflow/path projection over canonical state.
5. Read-only anti-sprawl frontier projection + operator/worker guidance.
6. Documentation that makes state/policy/execution ownership unambiguous.

---

## CAUSAL MAP

```text
Hermes card + links + run identity (SQLite)
   ↓
Labs resolves worker + policy
   ↓
worker/global/board/workflow/path policy
   ↓
native card overrides win last
   ↓
canonical frontier snapshot
   ↓
local bridge PID
   ↓
SSH/Docker executor
   ↓
real Git worktree OR ordinary workspace
   ↓
whole model/API OR one distributed inference gateway
   ↓
worker result + optional Git result ref
   ↓
expected_run_id fenced completion
```

No v0.2 feature sits outside this chain merely for novelty.

---

## ROOK

**Score: 9.4/10 — no hard veto.**

Corrections:

- state remains exclusively upstream SQLite;
- no Labs scheduler/API/task ledger added;
- active upstream Git/worktree ownership is reused, not duplicated;
- Git result capture is non-destructive: result ref, never silent branch reset/merge;
- remote host never receives controller origin credentials;
- exact run/claim fencing remains intact;
- frontend/tree work is a projection, not a second board implementation;
- hard graph-admission mutation was *not* smuggled into the compatibility patch.

Remaining ROOK debt: `workspace="git"` needs real multi-host failure/restart testing, especially remote disconnect during bundle/result transfer and cleanup of abandoned remote worktrees.

## NOVA

**Score: 9.3/10.**

The release now addresses the actual reviewer experience:

- coding workers get Git instead of flattened files;
- different workflows/paths can select different models/prompts;
- card overrides still work remotely;
- board state/backend is no longer ambiguous;
- nested paths can be read vertically;
- sprawl is visible and policy-bounded instead of hand-waved.

Remaining NOVA gap: frontier limits are advisory/diagnostic in v0.2 rather than a host-orchestrator `kanban_create` hard gate. This is explicit, not hidden.

## SURGE

**Score: 9.7/10.**

The feedback was converted immediately into code, tests, CLI surfaces, docs, and a release artifact instead of a roadmap-only reply.

## WINNING ACTION

Ship **v0.2 as a thin composition release**: Git-native remote workers + adaptive policy + vertical projection + frontier evidence, while preserving Hermes ownership and tracking the upstream seams that should eventually delete Labs code.

## PARALLEL ACTION

- Real Mac/Linux SSH worker compatibility matrix.
- Real Shard/MLX distributed-model worker test.
- Design/submit a narrow upstream card-admission hook so frontier budgets can become a hard orchestrator guard without Labs taking board ownership.
- Optional dashboard tree view that consumes existing upstream API data.

## COLLABORATION ACTION

- Test/review #91981 rather than reimplement its task-runtime authority.
- Feed external-spawn findings into #70547.
- Feed distributed-worker lifecycle findings into #29244.
- Invite users with real Shard/MLX clusters to exercise `monster-shard` as one logical worker.

## TRUE BLOCKER

`FINISHED_FOR_REAL` still requires hardware evidence not available in this build environment:

- real SSH + Docker host;
- disconnect/reconnect during remote Git execution;
- cleanup/recovery of a stranded remote worktree;
- real distributed inference endpoint (ideally multi-Mac) used by one Hermes worker.

## NEXT EXECUTABLE STEP

Publish/update v0.2, then run one disposable coding card with `workspace="git"` on a real remote node. Verify the fetched `refs/hermes-kanban-labs/results/<task-run>` commit, kill the SSH path mid-run once, and record cleanup/recovery evidence.

## EVIDENCE PRODUCED

- 26/26 Python tests passing before packaging.
- Existing subprocess bridge → SSH → Docker-shim smoke still passes.
- Existing lost-claim and remote-nonzero negative paths still pass.
- Policy precedence test proves global → board → workflow → nested paths → card override.
- Remote command test proves card execution spec replaces static worker model/provider and carries reasoning + skills.
- Real temporary Git repositories prove exact `HEAD` bundles can materialize into a remote-style bare ref without origin credentials.
- Frontier test proves saturation projection is read-only against canonical-style SQLite state.
- Tree test proves workflow/path indentation and parent/child dependency metadata coexist.
- No-second-authority test still rejects Labs-owned SQLite/scheduler creation.
- Upstream compatibility contract smoke passes.

## ARTIFACTS PRODUCED

- Git-native SSH/Docker executor.
- Adaptive policy resolver.
- Frontier projection.
- Vertical tree/JSON projection.
- `hkl frontier` and `hkl tree` commands.
- Workflow/Git/anti-sprawl architecture docs.
- Updated public release ZIP/wheel/checksums.

## STATUS

**FINISHED** — a materially stronger publishable alpha. **Not FINISHED_FOR_REAL** until the external hardware/restart/recovery journey is witnessed end-to-end.
