# Hermes Kanban Labs v0.1.0 — Public Experimental Alpha

This is the first community release candidate.

## Purpose

Expose advanced Hermes Kanban worker patterns to power users now while remaining downstream-compatible with current `NousResearch/hermes-agent/main`.

## Included

- one canonical upstream Hermes Kanban authority;
- minimal current-main compatibility patch for custom `spawn_fn` + non-profile assignees;
- mixed normal-profile and external worker dispatch;
- SSH/Docker Hermes subworkers;
- standalone and `shard_cluster` logical worker configurations;
- claim heartbeat and exact-run completion fencing;
- remote cancellation on claim loss;
- upstream-owned retry/crash/failure-breaker behavior;
- optional rsync workspace transport;
- current-main drift CI and conservative rebase helper.

## Verification

Release convergence result:

```text
17 passed
UPSTREAM CONTRACT PASS
SMOKE PASS
```

Additional packaging verification:

- source compiles with Python 3.13;
- clean `pip --target` install succeeded;
- wheel build succeeded;
- CLI entry point loaded from installed package;
- real subprocess smoke exercised bridge -> SSH shim -> Docker shim -> exact-run completion;
- failure subprocess smoke proved non-zero remote exit cannot false-complete;
- lost-claim test proved remote cancellation + stale-run completion denial.

## Upstream compatibility

Last verified current-main SHA at release assembly:

`3f36c87e1ebdfbf7d14a88229dc9be222c12ea89`

The scheduled `upstream-main-drift` workflow deliberately tests latest `main`, not only this pin.

## Honest limitation

The assembly environment did not provide a Docker daemon or a second SSH-accessible physical host. Therefore this release is **not** labeled hardware-accepted. The first community acceptance run should use `hkl doctor --pull` and one disposable Kanban card on a real worker machine, then record the exact hardware/model/upstream SHA.
