# AGENTS.md — Docs Tree Index

Navigation index for `docs/`. Helps agents find the right document fast.

Active direction is currently anchored by `todo.md` and `plans/multi-tier-runtime-implementation-plan-2026-03-24.md`.

## Docs Tree

| Path | Purpose |
|---|---|
| `todo.md` | Current truth, active tasks, blockers |
| `north-star.md` | Desired end state |
| `architecture-overview.md` | Organizing logic |
| `repo-index.md` | Exhaustive repo map |
| `ALS-reference/` | ALAS as reference system |
| `RES-research/` | Research notes and synthesis |
| `memory/` | Dated lessons learned |
| `prework/` | Corpus alignment and data-gathering procedures |
| `runtime/` | Runtime contracts, backend lessons, health design, tool requirements |
| `dev/` | Developer workflow docs (testing strategy, ADB integration testing) |
| `vlm/` | Model profiles, task contracts, prompt guidance |
| `plans/` | Active planning docs |
| `workflows/` | Workflow inventory |
| `agentPrompts/` | Code-linked prompt rationale |

## Find The Right Document

| Question | Document |
|---|---|
| What is the repo trying to do? | `north-star.md` |
| What should I work on right now? | `todo.md` |
| What is the runtime architecture? | `plans/multi-tier-runtime-implementation-plan-2026-03-24.md` |
| What are the backend lessons? | `runtime/backend-lessons.md` |
| What is ALAS in this repo? | `ALS-reference/ALS-overview.md` |
| What are the ALAS live-run rules? | `ALS-reference/ALS-live-ops.md` |
| How do we test ADB/emulator? | `dev/testingADB.md` |
| What VLM models do we use? | `vlm/VLM-model-profiles.md` |
| What VLM tasks exist? | `vlm/VLM-task-contracts.md` |
| How do VLM prompts work? | `vlm/VLM-prompts.md` |
| How to run local models? | `vlm/llama-swap-quickstart.md` |
| What workflows exist in Azur Lane? | `workflows/azur-lane-workflows.md` |
| How to review corpus data? | `prework/corpus-review-playbook.md` |
| What lessons should not be relearned? | `memory/` |
| How is the repo organized? | `architecture-overview.md` |
| Where is everything? | `repo-index.md` |

## Domain Rule

Only two explicit documentation domains:
- `ALS-reference/` — ALAS as reference system
- `RES-research/` — research and synthesis

Everything else is a knowledge bucket, not a domain.

## Overlap Hotspots

### Runtime boundary
- `backend-lessons.md` owns backend constraints
- `plans/multi-tier-runtime-implementation-plan-2026-03-24.md` owns architecture and implementation steps

### VLM family
- `VLM-overview.md` indexes and frames
- `VLM-model-profiles.md` owns backend config
- `VLM-task-contracts.md` owns task I/O
- `VLM-prompts.md` owns prompt guidance only
