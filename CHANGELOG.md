# Changelog

## 0.1.0 — experimental alpha

- Reframed project as a thin power-user extension to upstream Hermes Kanban.
- Removed the previous separate Fleet SQLite/control-plane design.
- Added minimal compatibility patch for current-main custom `spawn_fn` + non-profile lanes.
- Added mixed upstream-profile and experimental worker dispatch.
- Added SSH/Docker worker backend using the official Hermes image.
- Added one-logical-worker sharded-inference configuration.
- Added claim heartbeat, exact-run completion fencing, lost-claim cancellation, and upstream-owned crash/retry behavior.
- Added optional rsync workspace transport.
- Added current-main drift workflow and conservative upstream sync script.
- Added unit, negative-path, and real subprocess command-shim smoke tests.
