# Sharded model worker

A sharded worker is **one Hermes Kanban worker backed by a distributed inference system**.

## Current real-world boundary

The public [leyten/shard](https://github.com/leyten/shard) engine is real distributed inference: it splits contiguous model-layer blocks across machines and streams activations through those stages. Its package also declares an optional Apple-Silicon MLX backend. At the time of this release, Shard's own state says scheduler/formation primitives exist while live control-plane integration is still the next step.

Therefore Hermes Kanban Labs v0.1 does **not** invent a fake stable Shard control API or claim that twenty Mac minis can be auto-formed by one Labs command today.

Instead, Labs defines the stable boundary it actually needs:

```text
Kanban assignee: monster-shard
        |
        v
ONE Dockerized Hermes subworker
        |
        v
one inference gateway URL
        |
        v
distributed model engine
   stage 1 -> stage 2 -> ... -> stage N
```

The distributed engine may be Shard, MLX distributed inference, another project, or a custom lab setup. The model-stage machines are not Kanban workers.

## Why this is useful now

It lets the Hermes side stabilize independently of the model-sharding side:

- Kanban sees one logical worker and one run.
- Claim/retry/review semantics stay ordinary Hermes semantics.
- A stronger cluster can replace a smaller cluster without changing the board.
- Shard/MLX contributors can improve model formation without becoming Kanban maintainers.
- When a turnkey Shard/MLX gateway recipe becomes stable, Labs can add it as bootstrap tooling without changing the worker contract.

## Mac mini target

A many-Mac cluster is an intended community acceptance target, not a release claim. A useful contribution should report:

- Mac model / chip / unified memory per node;
- interconnect (Ethernet / Thunderbolt / other);
- sharding engine + commit;
- model + quantization;
- number of stages;
- gateway URL shape;
- tokens/sec and time-to-first-token;
- restart / node-loss behavior;
- the Hermes Kanban Labs + upstream Hermes SHAs used.
