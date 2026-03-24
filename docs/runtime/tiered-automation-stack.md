# Tiered Automation Prototype Status

This document describes the current prototype/scaffold only.

It is not the canonical runtime architecture plan.

For the runtime blueprint, use:
- [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)

For the emulator transport companion, use:
- [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)

For the Tier-2 prompt contract, use:
- [docs/agentPrompts/tiered-automation-tier2.md](/mnt/c/Users/pmacl/.codex/worktrees/4587/MasterStateMachine/docs/agentPrompts/tiered-automation-tier2.md)

## Purpose

Answer four narrow questions:

- what is implemented today
- what is still prototype-only
- where the prototype diverges from the canonical plan
- what would need to change to bring it into alignment

## Current Prototype

The current prototype lives in:
- [tiered_automation.py](/mnt/d/_projects/MasterStateMachine/scripts/tiered_automation.py)

What it currently does:
- defaults `resolve` to a Tier-2-first VLM grounding path
- exposes an `observe-act` command that captures, resolves, taps, and captures again
- supports transport selection for capture through configured `adb` or `droidcast`
- exposes a `capture` command for transport validation and screenshot debugging
- keeps a manifest-backed Tier-1 template cache as an explicit prototype-only opt-in path
- supports two-shot Tier-2 retries via `--retry`, including previous-attempt context in the second grounding call
- emits structured resolver output for `lookup`, `register`, `resolve`, and `observe-act`
- performs a simple pixel-diff check after execution and reports `executed_verified` vs `executed_unverified`

What it does not do:
- execute actions itself
- own a trusted full runtime loop
- implement semantic embeddings or vector retrieval
- implement teacher escalation or distillation

## Prototype-Only Status

This scaffold is intentionally limited:

- Tier 1 is deterministic template matching, not semantic retrieval
- Tier 2 is now the default resolution path, but it is still a thin early runtime slice
- there is no Tier 3
- post-action verification is only a cheap frame-difference check, not a trusted semantic verifier
- there is no operator-facing runtime contract

It should be treated as implementation scaffolding and experimentation support, not as the recommended runtime direction.

## Divergence From The Canonical Plan

The canonical runtime plan says:

- Phase 1: Tier 2 VLM baseline first
- Phase 2: semantic Tier 1 cache with hit/hint/miss
- Phase 3: teacher escalation and distillation

The current prototype diverges in these ways:

- it still carries an optional template-first Tier 1 prototype instead of a semantic cache
- it has only hit/miss/error routing in the prototype cache path, not hit/hint/miss
- it has no semantic embedding cache
- it has no teacher model path
- it has no strong post-action verification loop
- it does not emit full operator-safe retry policies beyond a basic fixed two-attempt Tier-2 retry

## Alignment Work Needed

To align the prototype with the canonical plan:

1. establish the Tier 2-first observe-act-observe baseline
2. replace template-first Tier 1 with semantic retrieval after real data is collected
3. add hint routing only if measured to be useful and safe
4. add post-action verification and invalidation
5. add Tier 3 escalation and distillation
6. add objective-scoped semantic cache insertion and collision policy with controlled promotion rules

## Current Validation Status

The prototype has only lightweight validation today:

- CLI parsing and script compilation
- basic manifest read/write behavior
- basic resolver status wiring
- thin capture/tap/capture plumbing for `adb` and configured `droidcast`
- `observe-act` structured paths for resolved execute, escalate, and error outcomes

It has not yet proven a trusted live runtime path.
