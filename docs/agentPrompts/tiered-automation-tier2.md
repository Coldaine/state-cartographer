# Tiered Automation Tier-2 Prompt Surface

## Code Links

- [scripts/tiered_automation.py](/mnt/d/_projects/MasterStateMachine/scripts/tiered_automation.py)
- [scripts/vlm_detector.py](/mnt/d/_projects/MasterStateMachine/scripts/vlm_detector.py)

## Purpose

This document explains the prompt-bearing LLM surface used by the Tier-2 path in `tiered_automation.py`.

`tiered_automation.py` does not define a separate embedded prompt. It relies on `vlm_detector.locate_element()` and changes the `target` text passed into that prompt surface, especially on retry.

This document exists because that runtime scaffold still depends on prompt-shaped behavior and the repo requires a code-linked rationale doc for that dependency.

## Prompt Surface Used By Tier 2

The Tier-2 path uses:

- `SYSTEM_PROMPT` in `vlm_detector.py`
- `ELEMENT_LOCATE_PROMPT` in `vlm_detector.py`

The important runtime-specific input is the `target` string built by `Tier2Router.locate()`.

## `SYSTEM_PROMPT`

### Strict Assistant Role

`You are a strict screenshot labeling assistant.`

Why it exists:
- narrows the model role to evidence extraction from screenshots

How it helps Tier 2:
- keeps the model in a constrained grounding mode instead of open-ended assistant behavior

### Request-Bound Evidence

`Use only the information provided in the request.`

Why it exists:
- prevents hidden assumptions about the game or workflow

How it helps Tier 2:
- keeps localization tied to the screenshot and supplied task context

### Uncertainty Bias

`Prefer explicit uncertainty over confident guessing.`

Why it exists:
- false positive taps are more expensive than escalations

How it helps Tier 2:
- supports the runtime policy that uncertain results should become `no_result` or escalation instead of silent guesses

### Exact JSON Requirement

`Return JSON that matches the requested schema exactly.`

Why it exists:
- the runtime parser expects structured machine-readable output

How it helps Tier 2:
- reduces parser fragility and keeps retries/validation deterministic

## `ELEMENT_LOCATE_PROMPT`

### Task Framing

`Locate the requested UI element in the screenshot set.`

Why it exists:
- frames the call as grounding rather than classification or free description

How it helps Tier 2:
- pushes the model toward a concrete target location and a usable bbox

### Target Element

`Target element: {target}`

Why it exists:
- the resolver needs the visual target stated explicitly

How it helps Tier 2:
- this is where `tiered_automation.py` injects the runtime instruction and retry guidance

Runtime-specific behavior:
- first attempt passes the user instruction directly
- retry appends previous-attempt context and asks for a different likely location if the prior hit was weak or wrong

Why that retry mutation exists:
- it gives the model concrete failure context without changing the underlying schema or backend contract
- it is the smallest useful retry strategy for the current Phase 1 scaffold

### Task Context

`Task context: {task_context}`

Why it exists:
- visually similar controls can mean different things in different workflows

How it helps Tier 2:
- narrows the likely interpretation space for the grounding request

## Output Fields Required By Tier 2

The prompt asks for:

- `found`
- `confidence`
- `rationale`
- `bbox`
- `recommended_followups`

How `tiered_automation.py` uses them:

- `found`
  - absence becomes `not_found`, not a guessed tap
- `confidence`
  - results below the runtime threshold are rejected as `low_confidence`
- `bbox`
  - converted into normalized center coordinates after sanity checks
- `rationale`
  - preserved in raw output for debugging even though it is not yet surfaced as a first-class runtime field
- `recommended_followups`
  - preserved in raw output for future escalation/recovery work

## Why This Helps The Specific Agent

This prompt surface fits the current runtime scaffold because it:

- produces a bounded grounding answer rather than prose
- allows explicit failure without forcing a guess
- supports a minimal retry mutation without adding a second prompt family
- gives enough structure for geometry validation before any action is executed

It is still only a Phase 1 scaffold. Stronger post-action semantic verification and richer retry policy belong in later runtime work.
