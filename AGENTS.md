# AGENTS.md

This file is the mandatory starting point.

## Required Reading

| Document | What It Covers |
|---|---|
| [todo.md](/mnt/d/_projects/MasterStateMachine/docs/todo.md) | Current truth, active work, blockers |
| [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/repo-index.md) | Exhaustive repo map |
| [architecture-overview.md](/mnt/d/_projects/MasterStateMachine/docs/architecture-overview.md) | How the repo is organized |
| [decisions.md](/mnt/d/_projects/MasterStateMachine/docs/decisions.md) | Decision log: Vulkan, pull architecture, capture deferral |
| [vlm-corpus-sweep-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/vlm-corpus-sweep-plan.md) | Multi-pass VLM labeling to build the state machine |
| [north-star.md](/mnt/d/_projects/MasterStateMachine/docs/north-star.md) | Long-horizon goals and desired end-state |
| [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md) | ALAS: the original automation, how to run it, why we're replacing it |
| [ALS-live-ops.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-live-ops.md) | Operational rules and vendor patches for running ALAS |

## Documentation Domains

Two explicit domains in the docs tree:

- `ALS` — ALAS: the original automation this project supersedes (still running daily until the runtime replaces it)
- `RES` — research, synthesis, hypotheses, and technical investigations

These live under:

- [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md)
- [RES-founding-synthesis.md](/mnt/d/_projects/MasterStateMachine/docs/RES-research/RES-founding-synthesis.md)

For the docs-only map, read [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md).

## High-Level Repo Map

| Path | Purpose |
|---|---|
| `vendor/` | External reference code (ALAS) |
| `data/` | Corpora, logs, screenshots, labels, truth artifacts |
| `docs/` | Agent knowledge layer |
| `scripts/` | Active scripts (corpus_cleanup, kimi_review, vlm_detector, stress_test_adb) |
| `state_cartographer/` | Python package: transport substrate (adb, maatouch, health, models, pilot facade) |
| `tests/` | Automated tests (transport unit tests + live smoke tests) |
| `configs/` | Project configuration (emulator serial, tool posture) |

For the expanded version, read [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/repo-index.md).

## Key Documentation Entry Points

| Document | Why It Matters |
|---|---|
| [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md) | ALAS: the original automation we're superseding, how to run it |
| [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md) | What multimodal models do in this project |
| [vlm-corpus-sweep-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/vlm-corpus-sweep-plan.md) | How we build the state machine from the corpus |
| [azur-lane-workflows.md](/mnt/d/_projects/MasterStateMachine/docs/workflows/azur-lane-workflows.md) | Workflow/task inventory |
| [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md) | How to review corpus stretches |
| [2026-03-24-corpus-review-lessons.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-24-corpus-review-lessons.md) | Lessons from corpus review |
| [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md) | Testing policy and live test plan |
