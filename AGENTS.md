# AGENTS.md

This file is the mandatory starting point.

Its job is repo-level indexing, not explanation. Use it to find the right project knowledge quickly.

## Required Reading

| Document | What It Covers |
|---|---|
| [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md) | Where the project actually stands right now. |
| [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/project/repo-index.md) | Exhaustive high-level map of code, docs, data, and retained artifacts. |
| [architecture-overview.md](/mnt/d/_projects/MasterStateMachine/docs/architecture-overview.md) | How the repo is organized: domains, knowledge buckets, and implementation axes. |
| [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md) | Current tactical plan and near-term rebuild priorities. |
| [north-star.md](/mnt/d/_projects/MasterStateMachine/docs/project/north-star.md) | Long-horizon goals and desired end-state behavior. |
| [documentation-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/project/documentation-playbook.md) | How documentation is organized and what must be updated when docs change. |

## Documentation Domains

Only these remain explicit domains in the docs tree:

- `ALS` — ALAS as reference system, corpus source, and comparison point
- `RES` — research, synthesis, hypotheses, and technical investigations

These live under:

- [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md)
- [RES-founding-synthesis.md](/mnt/d/_projects/MasterStateMachine/docs/RES-research/RES-founding-synthesis.md)


For the docs-only map, read [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md).

## High-Level Repo Map

This is the minimal filesystem map you should keep in mind:

| Path | Purpose |
|---|---|
| `vendor/` | External reference code, especially ALAS |
| `data/` | Corpora, logs, screenshots, labels, and other truth artifacts |
| `docs/` | Agent knowledge layer |
| `scripts/` | Current active script-shaped tooling |
| `quarantine/` | Unsupported retained material, if any remains |
| `examples/` | Reference/example artifacts |

For the expanded version, read [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/project/repo-index.md).

## Key Documentation Entry Points

| Document | Why It Matters |
|---|---|
| [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md) | Why ALAS matters and how to use it correctly as reference material |
| [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md) | What multimodal models are expected to do in this project |
| [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md) | What the eventual live runtime is supposed to own |
| [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md) | Observation-side contracts and what is still only design guidance |
| [azur-lane-workflows.md](/mnt/d/_projects/MasterStateMachine/docs/workflows/azur-lane-workflows.md) | Workflow/task inventory and substate complexity |
| [alas-build-plan.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-build-plan.md) | Operational program for deriving artifacts from ALAS |
| [2026-03-24-corpus-review-lessons.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-24-corpus-review-lessons.md) | Compact lessons learned from the corpus review reset and first direct adjudication pass |
| [master-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/master-plan.md) | Archived long-horizon plan context still worth knowing |

## Examples and Meta

| Path | Purpose |
|---|---|
| `examples/azur-lane/` | Current Azur Lane example/reference artifacts |
| `README.md` | GitHub-facing project overview |
| `.githooks/pre-commit` | Local formatting hook used by the repo |
