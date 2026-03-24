# Runtime Overview

> Historical note: this document folds together material that previously lived in `OBS-overview.md`, `NAV-overview.md`, `EXE-overview.md`, `AUT-overview.md`, and the later standalone `operator-model.md`.

## Purpose

Describe what the future live runtime is supposed to own, and what should count as operator-facing, without pretending that the current repo ships that runtime today.

See also:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md)
- [backend-hardening.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/backend-hardening.md)

## What Runtime Means Here

The runtime is the live supervised automation system.

A re-earned runtime would be responsible for:
- interacting with the live emulator or device
- packaging observational context
- choosing and executing trusted actions
- verifying progress
- recovering from known failures
- escalating with structured context when it cannot continue safely

## What Runtime Is Not

- not the corpus pipeline
- not the research archive
- not the VLM profile library by itself
- not ALAS
- not quarantined bridge experiments

## Operator-Facing Model

The intended long-term operator model is:
- the runtime owns screenshot capture, action execution, verification, recovery, and event recording
- the agent operates through higher-level control surfaces rather than micromanaging taps, screenshots, and retries directly
- escalation should carry structured context rather than forcing the operator to rediscover the situation from scratch

An operator-facing surface should:
- clearly state what it is allowed to do
- own its own preflight and verification requirements
- expose explicit success and failure semantics
- distinguish normal execution from escalation

These do **not** count as operator-facing just because they exist:
- reference-system tools
- corpus cleanup scripts
- ad hoc screenshot or labeling helpers
- quarantined bridge code
- historical or planned entrypoints

## Current Status

The repo does not currently ship a supported live runtime or a re-earned live operator path.

What remains today is mostly:
- corpus and prework tooling
- VLM labeling and adjudication tooling
- retained documentation of runtime constraints, failure modes, and historical attempts

Historical docs that mention canonical runtime entrypoints should be treated as project memory, not current guarantee.

## Runtime Concerns That Survive The Old Layering

The old `OBS/NAV/EXE/AUT` split still names useful concerns, but they now survive as sub-concerns inside runtime design:
- observation and context packaging
- movement and transition logic
- action execution and verification
- scheduling, recovery, and escalation

## Required Runtime Capabilities

A rebuilt runtime should eventually own:
- screenshot capture and freshness proof
- action execution primitives with verification hooks
- session and workflow context
- state and substate grounding support
- workflow execution and recovery
- structured escalation payloads

## Current Gaps

- no supported live backend
- no supported operator entrypoint
- no trusted runtime contract between observation, VLM, and execution
- no explicit assignment contract that tells the agent what to attempt and how success is judged

## Runtime Documents

The runtime knowledge docs that remain after consolidation are:
- [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md)
- [backend-hardening.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/backend-hardening.md)
