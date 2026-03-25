# AGENTS.md — Docs Tree Index

Navigation index for `docs/`. Helps agents find the right document fast.

## Docs Tree

| Path | Purpose |
|---|---|
| `todo.md` | Current truth, active tasks, blockers |
| `north-star.md` | Desired end state |
| `architecture-overview.md` | Organizing logic |
| `repo-index.md` | Exhaustive repo map |
| `documentation-playbook.md` | Doc workflow rules |
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
| What control tools do we use? | `plans/substrate-and-implementation-plan.md` |
| What is the runtime architecture? | `plans/multi-tier-runtime-implementation-plan-2026-03-24.md` |
| What does the runtime own? | `runtime/runtime-overview.md` |
| What must a control tool provide? | `runtime/agent-control-tool-requirements.md` |
| How does health/heartbeat work? | `runtime/health-heartbeat-logging.md` |
| What are the backend lessons? | `runtime/backend-lessons.md` |
| What does observation return? | `runtime/observation-contracts.md` |
| What is ALAS in this repo? | `ALS-reference/ALS-overview.md` |
| What are the ALAS live-run rules? | `ALS-reference/ALS-live-ops.md` |
| What is the testing policy? | `dev/testing-strategy.md` |
| How do we test ADB/emulator? | `dev/testingADB.md` |
| What VLM models do we use? | `vlm/VLM-model-profiles.md` |
| What VLM tasks exist? | `vlm/VLM-task-contracts.md` |
| How do VLM prompts work? | `vlm/VLM-prompts.md` |
| How to run local models? | `vlm/llama-swap-quickstart.md` |
| What workflows exist in Azur Lane? | `workflows/azur-lane-workflows.md` |
| What ALAS artifacts matter? | `prework/alas-artifacts.md` |
| How to review corpus data? | `prework/corpus-review-playbook.md` |
| What lessons should not be relearned? | `memory/` |
| How is the repo organized? | `architecture-overview.md` |
| Where is everything? | `repo-index.md` |
| How should docs be added/updated? | `documentation-playbook.md` |

## Domain Rule

Only two explicit documentation domains:
- `ALS-reference/` — ALAS as reference system
- `RES-research/` — research and synthesis

Everything else is a knowledge bucket, not a domain.

## Overlap Hotspots

### Runtime boundary
- `runtime-overview.md` owns scope
- `observation-contracts.md` owns observation shape
- `backend-lessons.md` owns backend constraints
- `health-heartbeat-logging.md` owns health tiers and events
- `agent-control-tool-requirements.md` owns tool acceptance criteria
- `plans/substrate-and-implementation-plan.md` owns tool selection and implementation steps

### VLM family
- `VLM-overview.md` indexes and frames
- `VLM-model-profiles.md` owns backend config
- `VLM-task-contracts.md` owns task I/O
- `VLM-prompts.md` owns prompt guidance only
