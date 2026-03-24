# Current Plan

## Purpose

This is the canonical current plan. It describes active work and standing constraints only.

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

What is not currently trusted:
- old graph/navigation/runtime script claims
- any implied live operator path that has not been re-earned

## Active Work

### Stabilize prework as the active implementation surface

- keep ALAS log alignment and corpus cleanup accurate
- make ALAS-derived build procedures explicit and current
- keep corpus and labeling workflows grounded in actual retained code

Active workstreams:
- ALAS-derived artifact building
- corpus cleanup and corpus hygiene
- log/frame alignment
- label ontology and review quality

### MEmu control stack

- canonical runtime blueprint in [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- emulator transport/integration companion in [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)
- ADB + DroidCast as the minimum viable stack
- first goal: prove observe-act-observe loop on a single MEmu session

## Standing Constraint: Runtime Gates

No new live-runtime architecture should be treated as active until these questions are answered:
- what is the first real capability being shipped?
- what proof counts as success?
- which truth sources are trusted, weak, or provisional?
- what is the exact assignment contract for the agent?
- what is the thinnest architecture that supports that capability?
- which interfaces must be trusted before new code is added?

## Linked Work Areas

- prework details: [alas-build-plan.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-build-plan.md) and [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
- VLM boundaries: [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md), [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md), [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md), [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md)
- runtime architecture plan: [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- runtime constraints and ownership: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- current prototype status: [tiered-automation-stack.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/tiered-automation-stack.md)
