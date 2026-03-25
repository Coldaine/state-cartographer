# Runtime Local Actor Prompts

## Code Link

- [runtime/actor/prompt_builder.py](/mnt/c/Users/pmacl/.codex/worktrees/4587/MasterStateMachine/runtime/actor/prompt_builder.py)

## Purpose

This document explains the prompt text embedded in the first-pass runtime Local Actor layer.

This prompt set is for the live runtime loop, not offline corpus review.

## Prompt Families In This File

- `build_actor_system_prompt()`
- `build_actor_user_prompt()`
- `build_verifier_system_prompt()`
- `build_verifier_user_prompt()`

## Local Actor Choice

The runtime uses `candidate generator + verifier/reranker`.

Why:
- it avoids a brittle single-coordinate answer path
- it exposes uncertainty explicitly
- it allows runtime governance to reject weak candidates before execution
- it keeps post-action verification separate from proposal generation

## `build_actor_system_prompt()`

Role:
- sets the model as a bounded local UI actor for a Unity game

Why it exists:
- keeps the model focused on grounded action proposals
- blocks drift into generic assistant behavior

How it helps:
- reinforces that only the current frame and compact context are valid inputs

## `build_actor_user_prompt()`

Task framing:
- asks for up to 3 bounded next actions

Why it exists:
- preserves alternative candidates when the screen is ambiguous
- supports later reranking and validation in runtime code

Context payload:
- includes only the compact context contract

Why it exists:
- avoids giant planner prompts
- keeps runtime governance in code rather than in sprawling prompt state

Transition-state field:
- requires one of the runtime transition categories

Why it exists:
- lets the actor acknowledge mid-transition or obstructed states explicitly
- prevents immediate false-failure assumptions

Candidate fields:
- `action_type`
- `confidence`
- `uncertainty`
- `rationale`
- `target_point`
- `bbox`
- `swipe_to`
- `keycode`
- `text`

Why they exist:
- runtime needs a machine-checkable action proposal
- `confidence` and `uncertainty` support rejection of weak proposals
- geometry fields keep actions grounded in the visible frame

## `build_verifier_system_prompt()`

Role:
- makes the model a post-action verifier instead of a planner

Why it exists:
- separates action proposal from action adjudication
- reduces leakage from “what should happen” into “did it happen”

## `build_verifier_user_prompt()`

Task framing:
- compares ordered before/after frames plus compact context and executed action

Why it exists:
- makes verification depend on visible transition evidence rather than raw pixel change alone

Output fields:
- `status`
- `confidence`
- `observed_state`
- `rationale`

Why they exist:
- `status` maps to runtime governance outcomes
- `confidence` supports conservative handling of uncertain changes
- `observed_state` helps the next loop iteration carry compact context

## Governance Boundary

These prompts do not decide retries, escalation, replay insertion, or trust thresholds.

Those remain runtime code responsibilities.
