# AGENTS.md — Docs Tree Index

> This file is the local index for `docs/`.

Its job is to help an agent navigate the documentation tree quickly, understand which document answers which question, and avoid creating more overlap inside `docs/`.

## What `docs/` Is For

`docs/` is the project knowledge layer.

It is persistent project memory for agents and collaborators:
- reference-system knowledge
- research
- project state
- planning
- workflow definitions
- runtime boundaries
- prework procedures
- VLM contracts

## Domain Rule

Only these remain explicit documentation domains:
- `ALS-reference/`
- `RES-research/`

Everything else in `docs/` is a knowledge bucket, not a domain.

## Docs Tree

- `ALS-reference/`
  - ALAS as reference system: overview, event schema, live-ops rules
- `RES-research/`
  - durable research notes, synthesis, and analysis
- `project/`
  - current reality, north star, repo index, validation posture
- `memory/`
  - dated lessons learned and preserved findings that should not be re-learned
- `prework/`
  - corpus alignment, cleanup, and ALAS-derived artifact building
- `runtime/`
  - live-system boundaries, observation contracts, backend hardening
- `vlm/`
  - model profiles, task contracts, prompt-layer guidance
- `plans/`
  - current and long-horizon planning docs
- `decisions/`
  - ADR-style decisions
- `workflows/`
  - workflow inventory and operational task descriptions
- `vendor-patches/`
  - retained patch/artifact bucket
- `architecture-overview.md`
  - top-level architecture and organizing logic

## Authoritative Starting Points By Question

- `What is the repo trying to do?`
  - `project/north-star.md`
  - `project/current-reality.md`
- `What is the current tactical plan?`
  - `plans/current-plan.md`
- `What is the long-horizon plan?`
  - `plans/master-plan.md`
- `How is the repo organized?`
  - `architecture-overview.md`
- `How should the live system be thought about?`
  - `runtime/runtime-overview.md`
  - `runtime/observation-contracts.md`
  - `runtime/backend-hardening.md`
- `What is ALAS in this repo?`
  - `ALS-reference/ALS-overview.md`
  - `ALS-reference/ALS-live-ops.md`
- `What is the VLM stack supposed to look like?`
  - `vlm/VLM-overview.md`
  - `vlm/VLM-model-profiles.md`
  - `vlm/VLM-task-contracts.md`
  - `vlm/VLM-prompts.md`
- `How do we work with corpus/log data?`
  - `prework/alas-build-plan.md`
  - `prework/corpus-review-playbook.md`
- `What recent lessons should we not relearn?`
  - `memory/2026-03-24-corpus-review-lessons.md`
- `What workflows exist?`
  - `workflows/azur-lane-workflows.md`
- `Where is the fuller repo map?`
  - `project/repo-index.md`

## Known Overlap Hotspots

These are the main places where docs can drift into duplication.

### 1. Repo navigation overlap
- `../AGENTS.md`
- `project/repo-index.md`

Rule:
- root `AGENTS.md` is the short repo entrypoint
- `project/repo-index.md` is the exhaustive repo map

### 2. Current truth vs strategy
- `project/current-reality.md`
- `project/north-star.md`
- `plans/current-plan.md`

Rule:
- `current-reality.md` owns what is true now
- `north-star.md` owns desired end state
- `current-plan.md` owns near-term change program

### 3. Runtime boundary overlap
- `runtime/runtime-overview.md`
- `runtime/observation-contracts.md`
- `runtime/backend-hardening.md`

Rule:
- `runtime-overview.md` owns runtime scope and operator-facing boundary
- `observation-contracts.md` owns observation contract shape
- `backend-hardening.md` owns backend constraints and salvage notes

### 4. VLM family drift
- `vlm/VLM-overview.md`
- `vlm/VLM-model-profiles.md`
- `vlm/VLM-task-contracts.md`
- `vlm/VLM-prompts.md`

Rule:
- `VLM-overview.md` should index and frame
- `VLM-model-profiles.md` owns backend/model capability configuration
- `VLM-task-contracts.md` owns task I/O and schema shape
- `VLM-prompts.md` owns prompt-layer guidance only

## Writing Rules For New Docs In `docs/`

- Do not create a new doc if an existing doc can absorb the responsibility cleanly.
- Do not create a new domain. Only `ALS` and `RES` are explicit domains here.
- Prefer one authoritative doc per question.
- If a new doc is necessary, define its boundary against neighboring docs immediately.
- If a doc is mostly indexing, keep it short.
- If a doc is mostly state/plan memory, make it explicit and dated where appropriate.

## When Editing Docs

Before changing or adding a doc, answer:
- what exact question does this doc answer?
- which existing doc is closest?
- why can that existing doc not absorb the change?
- what overlap risk does the new placement create?

If those answers are weak, the doc probably should not be added.

## See Also

- root [AGENTS.md](/mnt/d/_projects/MasterStateMachine/AGENTS.md) for repo-level entrypoint guidance
- [architecture-overview.md](/mnt/d/_projects/MasterStateMachine/docs/architecture-overview.md) for the organizing model behind this tree
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/project/repo-index.md) for the exhaustive repo map
