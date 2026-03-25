# Runtime Overview

## Purpose

What the live runtime is supposed to own, stated plainly.

## What We Are Building

A supervised automation runtime for Azur Lane daily operations that:
- Borrows emulator control from adbutils + MaaTouch (see [substrate-and-implementation-plan.md](../plans/substrate-and-implementation-plan.md))
- Uses local VLM models for screen understanding (see [VLM-overview.md](../vlm/VLM-overview.md))
- Owns the observe-decide-act-verify loop
- Owns workflow planning, recovery, and escalation
- Persists structured evidence for every action

## What Runtime Means

The runtime is the live supervised automation system. It is responsible for:
- Interacting with the live emulator through borrowed control tools
- Packaging observational context for VLM classification
- Choosing and executing actions
- Verifying that actions had the intended effect
- Recovering from known failures
- Escalating with structured context when it cannot continue safely

## What Runtime Is Not

- Not the corpus pipeline
- Not the research archive
- Not the VLM model library
- Not ALAS
- Not the transport layer (that's adbutils + MaaTouch)

## Operator Model

- The runtime owns action validation, verification, recovery, and event recording
- The runtime borrows attachment, screenshot, and input primitives from adbutils + MaaTouch
- The agent operates through higher-level control surfaces, not micromanaging taps and retries
- Escalation carries structured context so the operator does not have to rediscover the situation

## Current Status

The repo does not currently ship a working runtime.

What exists today:
- Corpus and prework tooling (kimi_review.py, vlm_detector.py, corpus_cleanup.py)
- Retained documentation of runtime constraints, failure modes, and lessons
- The substrate decision and implementation plan
- Empty transport directory ready for rebuild

What needs to be built:
1. Transport layer on adbutils + MaaTouch (Step 1-3 of the substrate plan)
2. Tier 2 VLM grounding loop (observe-act-observe on real device)
3. Multi-step workflow execution with stuck detection
4. Structured NDJSON event logging
5. Recovery ladder implementation

## Required Runtime Capabilities

A rebuilt runtime must own:
- Freshness/health proof over the observation path
- Action validation and verification hooks
- Session and workflow context
- State and substate grounding
- Workflow execution and recovery
- Structured escalation payloads

## Runtime Documents

- [substrate-and-implementation-plan.md](../plans/substrate-and-implementation-plan.md) — what tools we use and how to build on them
- [multi-tier-runtime-implementation-plan-2026-03-24.md](../plans/multi-tier-runtime-implementation-plan-2026-03-24.md) — tiered architecture (Tier 2 VLM baseline, Tier 1 cache, Tier 3 teacher)
- [observation-contracts.md](observation-contracts.md) — what the runtime asks of observation
- [backend-lessons.md](backend-lessons.md) — lessons from past emulator work
- [health-heartbeat-logging.md](health-heartbeat-logging.md) — readiness tiers, heartbeats, event schema
- [agent-control-tool-requirements.md](agent-control-tool-requirements.md) — acceptance criteria for borrowed tools
