# Git-native remote workspaces

`workspace = "git"` preserves a real Git worktree across the SSH boundary.

## Transport

1. Controller validates the resolved Hermes workspace is a Git worktree.
2. The exact local `HEAD` is packed into a Git bundle.
3. The remote host stores/reuses a bare repository cache keyed by the controller's Git common-dir identity.
4. A run-specific remote worktree is created from that exact bundled commit.
5. Dirty and untracked controller files are overlaid with `rsync --exclude=.git` so the remote worktree keeps its own Git administrative link.
6. Docker mounts that run-specific worktree as `/workspace`.
7. Files are synced back after execution.
8. Remote `HEAD` is bundled and fetched into the controller as:

   `refs/hermes-kanban-labs/results/<task-run>`

Labs never silently resets, merges, or moves the user's current branch. The fetched result ref is evidence the operator/agent can inspect, diff, cherry-pick, merge, or discard.

## Why bundles

The remote host does not need the controller's GitHub/GitLab credentials or access to the origin. The controller transfers only Git objects reachable from the task's exact base commit plus the workspace overlay.

## Upstream ownership

Labs' remote transport is intentionally complementary to upstream PR #91981, which owns task-scoped Docker worktree authority inside Hermes itself. Labs should consume that upstream behavior as it lands rather than reimplement its security rules.
