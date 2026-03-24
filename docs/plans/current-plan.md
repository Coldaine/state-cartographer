# Current Plan

> Historical note: moved from `docs/plans/plan.md`. Older observation-first runtime language is preserved only where still useful as context.

## Purpose

This is the canonical current plan.

It should describe current work and current gating questions only. Older implementation claims belong in historical docs, not here.

See also:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [north-star.md](/mnt/d/_projects/MasterStateMachine/docs/project/north-star.md)
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/project/repo-index.md)

## Current State

The repo is in a data-first rebuild phase.

What is currently trusted:
- the ALAS reference system under `vendor/AzurLaneAutoScript/`
- corpus and log artifacts under `data/`
- the small active script surface described in [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- the docs tree as the agent knowledge layer
- the preserved proof that direct MEmu `fb0` capture can return non-black Azur Lane frames on `127.0.0.1:21513`

What is not currently trusted:
- old graph/navigation/runtime script claims
- any implied live operator path that has not been re-earned
- older plan language that assumes deleted scripts still exist

## Immediate Goals

### 1. Finish documentation consolidation

- remove or merge stale overlap docs
- keep only a few durable docs per question
- make folder roles explicit and narrow
- preserve project memory without keeping dead planning artifacts alive

### 2. Stabilize prework as the active implementation surface

- keep ALAS log alignment and corpus cleanup accurate
- make ALAS-derived build procedures explicit and current
- keep corpus and labeling workflows grounded in actual retained code

### 3. Tighten the VLM contract surface

- separate model profiles, task contracts, and prompt guidance cleanly
- stop carrying backend/config constraints inside prompt prose
- keep VLM work focused on offline labeling/adjudication until a live path is re-earned

### 4. Re-earn runtime only after the gates are answered

No new live-runtime architecture should be treated as active until these questions are answered clearly:
- what is the first real capability being shipped?
- what proof counts as success?
- which truth sources are trusted, weak, or provisional?
- what is the exact assignment contract for the agent?
- what is the thinnest architecture that supports that capability?
- which interfaces must be trusted before new code is added?

For the current MEmu runtime branch, one transport fact is now re-earned:

- direct framebuffer capture through `adb root` + `/dev/graphics/fb0` works on the tested instance

What is still not re-earned:

- repeated transport stability across a full session
- final channel-order validation
- action execution plus post-action verification
- a supported operator-facing runtime entrypoint

## Active Workstreams

### Prework

- ALAS-derived artifact building
- corpus cleanup and corpus hygiene
- log/frame alignment
- label ontology and review quality

### VLM

- model profile cleanup
- task contract cleanup
- prompt/config separation
- offline evaluation and adjudication flow

### Docs

- collapse duplicate docs
- mark historical docs as historical
- keep `AGENTS.md` and `repo-index.md` aligned with actual repo structure

## Near-Term Exit Criteria

The current pass is successful when:
- the docs tree no longer implies deleted code still exists
- each major question has one authoritative doc
- prework docs match the retained script surface
- VLM docs reflect current model/config reality rather than 2024-era prompt habits
- the next runtime step is blocked by explicit gates rather than hidden assumptions

## Linked Work Areas

- MEmu control-stack plan lives in [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)
- MEmu transport implementation gates and TDD work order live in [memu-fb0-requirements-and-tdd-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-fb0-requirements-and-tdd-plan.md)
- prework details live in [alas-build-plan.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-build-plan.md) and [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
- VLM boundaries live in [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md), [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md), [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md), and [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md)
- runtime constraints live in [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- tiered runtime implementation (3-tier architecture with semantic cache) lives in [tiered-runtime-implementation.md](/mnt/d/_projects/MasterStateMachine/docs/plans/tiered-runtime-implementation.md) — activates after the MEmu transport slice is proven and the current gates are answered
