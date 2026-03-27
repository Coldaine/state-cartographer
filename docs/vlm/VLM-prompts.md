# VLM Prompts

> Historical note: this document replaces the old split prompt-doc pattern from `docs/prompts/vlm/`.

## Purpose

This document captures prompt-layer guidance only.

Prompts are the natural-language instruction layer sitting on top of model profiles and task contracts. They should stay minimal.

See also:
- [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md)
- [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md)
- [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md)

## What Prompt Text Should Do

Prompt text should provide only the irreducible task instruction required for the current call.

It should help the model:

- attend to the right evidence
- use the provided task context
- respect the candidate set or target description
- prefer uncertainty over fabrication

## What Prompt Text Should Not Own

Do not put these responsibilities into prompts when the stack can define them elsewhere:

- backend selection
- structured output mode
- schema enforcement
- reasoning mode
- image packing policy
- retry policy
- adjudication policy
- output field definitions

Those belong in profiles, task contracts, or pipeline logic.

## Prompt Families

### Classification

Use for candidate-based substate selection.

Prompt text should focus on:

- the task context
- the candidate labels
- any sequence context that matters

### Grounding

Use for finding visible UI targets or cues.

Prompt text should focus on:

- the target description
- relevant task context
- the desired grounding form

### Comparison / Adjudication

Use for frame-to-frame comparison or conflict resolution.

Prompt text should focus on:

- what is being compared
- what decision is required
- what evidence should break the tie

## Operational Rule

If a prompt starts carrying configuration, schema, or backend policy, that content is in the wrong file.

File-specific rationale for prompt-bearing code belongs in `docs/agentPrompts/`, with a companion doc that links to the code file, justifies each meaningful prompt part, and explains how each part helps the model on that task.
