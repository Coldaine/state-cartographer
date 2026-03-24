# VLM Prompts

> Historical note: this document replaces the old split prompt-doc pattern from `docs/prompts/vlm/`.

## Purpose

This document captures prompt policy for the multimodal pipeline.

The prompts are part of the system, but they are not the whole system.

## What Prompts Should Do

Prompts should provide only the irreducible natural-language instruction required for the task.

They should not carry responsibilities that belong elsewhere.

## What Belongs Outside Prompt Text

Do not rely on prompt wording for things the stack can enforce directly:

- structured output mode
- JSON/schema enforcement
- reasoning policy
- backend selection
- image packing policy
- retry/adjudication policy

Those belong in model profiles, task contracts, and pipeline logic.

## Shared Prompt Assumptions

Across tasks, prompt text should:

- stay grounded in the supplied evidence
- prefer uncertainty over fabricated certainty
- use task context when provided
- avoid broad hidden assumptions about the application state

## Classification Prompt Family

Use for choosing among candidate labels or substates.

Prompt text should focus on:

- the task context
- the candidate set
- any sequence context that matters

Avoid telling the model to invent a global taxonomy.

## Grounding Prompt Family

Use for locating visible elements.

Prompt text should focus on:

- the target description
- relevant task context
- the desired form of grounding result

Avoid pretending a point estimate is always enough when the task really needs a region or uncertainty.

## Comparison / Adjudication Prompt Family

Use when comparing frames or resolving disagreements.

Prompt text should focus on:

- what is being compared
- what decision must be made
- what evidence should break the tie

## Current Operational Direction

- use multi-image context when a single frame is insufficient
- keep prompt text minimal
- move more behavior into profiles and task contracts over time
