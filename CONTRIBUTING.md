# Contributing

Hermes Kanban Labs is for power users proving advanced Kanban compositions before every upstream interface is finalized.

## Contribution rule

Good changes:

- make an existing Hermes primitive usable on remote/odd hardware;
- preserve upstream card/workflow semantics across an experimental executor;
- improve Git/worktree transport without competing with upstream task authority;
- add failure/recovery evidence;
- improve vertical/tree projections or policy inspection using canonical state;
- add a model/inference backend adapter without turning model shards into board workers;
- remove Labs code because upstream now provides it natively.

Please do **not** add a second task scheduler, board DB, dependency engine, retry ledger, workflow state store, or duplicate board REST API.

## Before opening a PR

```bash
./scripts/smoke.sh
git diff --check
```

For upstream-integration work:

```bash
python scripts/apply_upstream_patch.py /path/to/hermes-agent
python scripts/verify_upstream_contract.py /path/to/hermes-agent
```

Check active upstream PRs/issues first. In particular, task-scoped Docker/worktree authority currently has active upstream ownership in #91981; collaborate/consume rather than reimplementing the same security contract in Labs.

For hardware-specific changes, include OS, architecture, Docker runtime, Hermes SHA, workspace mode, model backend, network shape, and at least one failure/recovery case.
