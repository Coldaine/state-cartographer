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

- `todo.md`
  - repo-wide execution tracker and blockers list
- `ALS-reference/`
  - ALAS as reference system: overview, live-ops rules
- `RES-research/`
  - durable research notes, synthesis, and analysis
- `north-star.md`
  - desired end state
- `repo-index.md`
  - exhaustive repo map
- `documentation-playbook.md`
  - docs workflow rules
- `memory/`
  - dated lessons learned and preserved findings that should not be re-learned
- `prework/`
  - corpus alignment, cleanup, and ALAS-derived artifact building
- `runtime/`
  - live-system boundaries, observation contracts, external tool requirements, and borrowed-tool intake/setup notes
- `dev/`
  - developer workflow docs (testing strategy, etc.)
- `vlm/`
  - model profiles, task contracts, prompt-layer guidance
- `plans/`
  - tactical planning docs and the canonical runtime architecture plan
- `workflows/`
  - workflow inventory and operational task descriptions
- `agentPrompts/`
  - code-linked prompt rationale docs for prompt-bearing LLM code
- `vendor-patches/`
  - retained patch/artifact bucket
- `architecture-overview.md`
  - top-level architecture and organizing logic

## Authoritative Starting Points By Question

- `What is the repo trying to do?`
  - `north-star.md`
  - `todo.md`
- `What is the current tactical plan?`
  - `todo.md`
- `What should we do next at the execution level?`
  - `todo.md`
- `How is the repo organized?`
  - `architecture-overview.md`
- `How should the live system be thought about?`
  - `plans/multi-tier-runtime-implementation-plan-2026-03-24.md`
  - `runtime/runtime-overview.md`
  - `runtime/observation-contracts.md`
  - `runtime/backend-lessons.md`
- `What must an external agent-facing emulator control tool already provide?`
  - `runtime/agent-control-tool-requirements.md`
- `How should the borrowed control tools be set up and evaluated locally?`
  - `runtime/borrowed-control-tool-setup.md`
- `How does the MEmu emulator path connect to the runtime work?`
  - `plans/memu-android-control-stack-2026-03-24.md`
- `Where is the transport implementation code?`
  - `state_cartographer/transport/` (package) and `scripts/memu_transport.py` (CLI)
- `How do I run transport probes?`
  - `python scripts/memu_transport.py --help`
- `What is ALAS in this repo?`
  - `ALS-reference/ALS-overview.md`
  - `ALS-reference/ALS-live-ops.md`
- `What is the testing policy?`
  - `dev/testing-strategy.md`
- `What is the VLM stack supposed to look like?`
  - `vlm/VLM-overview.md`
  - `vlm/VLM-model-profiles.md`
  - `vlm/VLM-task-contracts.md`
  - `vlm/VLM-prompts.md`
  - `vlm/llama-swap-quickstart.md`
- `How do we work with corpus/log data?`
  - `prework/alas-artifacts.md`
  - `prework/corpus-review-playbook.md`
- `What recent lessons should we not relearn?`
  - `memory/2026-03-24-corpus-review-lessons.md`
  - `memory/2026-03-25-memu-transport-probe-results.md`
- `What workflows exist?`
  - `workflows/azur-lane-workflows.md`
- `Where is the fuller repo map?`
  - `repo-index.md`
- `How should docs be added or updated?`
  - `documentation-playbook.md`

## Known Overlap Hotspots

These are the main places where docs can drift into duplication.

### 1. Repo navigation overlap
- `../AGENTS.md`
- `repo-index.md`

Rule:
- root `AGENTS.md` is the short repo entrypoint
- `repo-index.md` is the exhaustive repo map

### 2. Current truth vs strategy
- `todo.md`
- `north-star.md`

Rule:
- `todo.md` owns current truth, repo-wide execution tracking, and the near-term change program
- `north-star.md` owns desired end state

### 3. Runtime boundary overlap
- `runtime/runtime-overview.md`
- `runtime/observation-contracts.md`
- `runtime/backend-lessons.md`
- `plans/multi-tier-runtime-implementation-plan-2026-03-24.md`
- `runtime/agent-control-tool-requirements.md`
- `runtime/borrowed-control-tool-setup.md`

Rule:
- `runtime-overview.md` owns runtime scope and operator-facing boundary
- `observation-contracts.md` owns observation contract shape
- `backend-lessons.md` owns backend constraints and salvage notes
- the multi-tier runtime plan owns canonical runtime architecture and phased sequencing
- `agent-control-tool-requirements.md` owns external tool selection criteria
- `borrowed-control-tool-setup.md` owns local intake/setup and compatibility spike procedure

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
- Any code containing an LLM prompt must have a separate companion doc under `agentPrompts/`.
- That companion doc must link to the code file, justify each meaningful prompt part, and explain how each part helps the model or agent on that task.
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
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/repo-index.md) for the exhaustive repo map
- [documentation-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/documentation-playbook.md) for documentation workflow rules
