# Todo

## Purpose

This document is the repo-wide execution tracker.

It exists to track immediate work, blockers, and deferred items without duplicating plan rationale that belongs elsewhere.

See also:
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)

## Current Focus

- stabilize the Phase 1 runtime scaffold into a usable observe-act-observe baseline

## Active Tasks

- strengthen post-action verification beyond raw frame diff
- add a multi-step `run-objective` loop with retry and stuck handling
- validate capture transport on a real MEmu session
- collect structured run artifacts before semantic cache work

## Blockers

- no confirmed live MEmu transport baseline has been proven in this worktree session
- no verified local VLM endpoint has been exercised end-to-end from the runtime scaffold

## Deferred

- semantic Tier 1 cache
- Tier 3 teacher escalation and distillation
