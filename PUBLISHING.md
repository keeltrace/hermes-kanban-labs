# Publishing / updating the public Labs repo

Public repository: `keeltrace/hermes-kanban-labs`

## Updating an existing clone to v0.2

Extract/copy the v0.2 source into a clean branch of the public repo, review the diff, then:

```bash
./scripts/smoke.sh
git diff --check
git add -A
git commit -m "feat: Git-native remote workers and adaptive Kanban policy (v0.2.0)"
git push origin main
```

Do not mechanically overwrite a dirty public checkout. The release ZIP is intentionally source-only and contains no `.git` history.

## Recommended release description

> Hermes Kanban Labs v0.2: Git-native SSH workers, adaptive board/workflow/path model policy, vertical tree projection, and anti-sprawl frontier budgets — while keeping upstream Hermes SQLite and lifecycle authority canonical.

## Hardware reports wanted

Please include:

- OS + architecture;
- Docker version/runtime;
- Hermes upstream SHA;
- `workspace` mode;
- model/inference backend;
- whether the worker is standalone or a sharded-model logical worker;
- happy-path result;
- one disconnect/cancel/recovery test;
- whether a Git result ref was returned and inspectable.

## Upstream strategy

If using a Hermes fork, keep `NousResearch/hermes-agent` as `upstream`, rebase frequently, and run `scripts/sync_upstream.sh`. Labs-specific core patches should shrink as equivalent upstream seams land.
