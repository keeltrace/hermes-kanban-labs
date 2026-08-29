# Publishing

The source tree is ready to become a public GitHub repository.

Recommended repository name: `hermes-kanban-labs`

Recommended description:

> Experimental power-user execution backends for Hermes Kanban — remote Docker workers, sharded-model superworkers, and current-main integration without a second scheduler.

## First publish with GitHub CLI

From the extracted directory:

```bash
git init
git branch -M main
git add .
git commit -m "feat: publish Hermes Kanban Labs experimental alpha"
gh repo create hermes-kanban-labs \
  --public \
  --source=. \
  --remote=origin \
  --push
```

Then enable GitHub Actions and open Discussions if you want hardware reports and design experiments separated from bug issues.

## Suggested first topics

- `good first issue`: test one real Linux SSH/Docker worker;
- `hardware`: Apple Silicon / Mac mini worker matrix;
- `inference`: Shard/MLX cluster gateway recipes;
- `upstream`: track #29244 / #70547 integration changes;
- `workspace`: preserve more upstream worktree semantics without duplicating branch authority;
- `security`: cancellation/replay/claim-loss adversarial tests.

## Fork mode

If the community prefers a directly runnable Hermes fork rather than a companion Labs repository, keep `NousResearch/hermes-agent` as `upstream`, rebase frequently, vendor/install this package in the fork, and use `scripts/sync_upstream.sh`. The architectural rule remains the same: upstream Kanban stays authoritative and Labs-specific core diffs should shrink over time.
