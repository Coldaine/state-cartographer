# Runtime Overview

> Historical note: this document folds together material that previously lived in `OBS-overview.md`, `NAV-overview.md`, `EXE-overview.md`, and `AUT-overview.md`.

## Purpose

Describe what the future live runtime is supposed to own, without using the retired `OBS/NAV/EXE/AUT` domain taxonomy as the primary organizing model.

## What Runtime Means Here

The runtime is the live supervised automation system.

It is responsible for:

- interacting with the live emulator or device
- packaging observational context
- choosing and executing trusted actions
- verifying progress
- recovering from known failures
- escalating with structured context when it cannot continue safely

## What Runtime Is Not

- not the corpus pipeline
- not the research archive
- not the VLM model-profile library by itself
- not ALAS

## Current Status

The repo does not currently ship a supported live runtime.

What remains in the repo today is mostly:

- corpus/prework tooling
- VLM labeling and adjudication tooling
- documentation of runtime requirements and historical attempts

## Runtime Concerns That Survive The Old Layering

The old `OBS/NAV/EXE/AUT` split still names real concerns, but they are now treated as sub-concerns inside runtime design:

- observation and context packaging
- movement and transition logic
- action execution and verification
- scheduling, recovery, and escalation

## Required Runtime Capabilities

A rebuilt runtime should eventually own:

- screenshot capture and freshness proof
- action execution primitives with verification hooks
- session and workflow context
- state/substate grounding support
- workflow execution and recovery
- structured escalation payloads

## Current Gaps

- no supported live backend
- no supported operator entrypoint
- no trusted runtime contracts between observation, VLM, and execution
- no explicit assignment contract that tells the agent what to attempt and how success is judged
