# Adaptive workflow policy

Hermes Kanban Labs v0.2 treats TOML as a **policy plane**, never as a second board database.
The canonical task, relationship, run, comment, and lifecycle state remains in Hermes' per-board SQLite database.

Policy resolution is deterministic:

```text
worker defaults
  -> global policy
  -> board policy
  -> workflow policy
  -> matching board paths (shallow -> deep)
  -> matching workflow paths (shallow -> deep)
  -> native Hermes card overrides
```

Prompts stack in that same order. Model/provider/reasoning values override earlier values.
Native card fields (`model_override`, `provider_override`, `reasoning_effort`, `skills`) are final authority so a remote worker never becomes less expressive than a local upstream worker.

`current_step_key` is treated as a dotted/slashed nested path. For example, a card at `research.deep.compare` matches both `research` and `research.deep` policies.

Example:

```toml
[boards.default.workflows.release]
prompt = "Produce reviewable release slices."

[boards.default.workflows.release.paths."research"]
model = "fast-model"

[boards.default.workflows.release.paths."research.deep"]
model = "strong-model"
reasoning_effort = "high"
```

This deliberately reuses the workflow/path fields already present on Hermes cards rather than creating a Labs-owned workflow ledger.
