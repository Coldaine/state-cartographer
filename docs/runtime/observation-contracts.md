# Observation Contracts

> Historical note: this document replaces the old pattern of treating observation as its own top-level domain.

## Purpose

Define what the runtime must be able to ask of the observation stack, regardless of which detectors, models, or retrieval strategies are currently in use.

See also:
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md)
- [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md)

## Core Runtime Questions

The runtime needs answers to questions like:
- what is visible right now?
- what workflow substate is this likely to be?
- what changed between the last frame and this one?
- where is the element I need to act on?
- how uncertain is this answer?

## Required Inputs

Observation calls should be able to use more than a single screenshot when needed.

Expected inputs:
- primary frame
- optional neighboring frames
- optional task or workflow context
- optional candidate labels or retrieved exemplars
- session context when available

## Required Outputs

Observation should return structured results, not free-form guesswork.

Expected fields vary by task, but should include some combination of:
- classification result or candidate set
- confidence and uncertainty
- grounding result (`bbox`, point, or `not found`)
- evidence summary grounded in visible content
- follow-up recommendation when evidence is weak

## Contract Boundaries

- model configuration belongs in backend and profile selection
- task schema belongs in the task contract
- prompt wording should be the thinnest layer
- runtime should consume typed outputs, not raw model strings

Do not push schema enforcement or backend policy into prompt prose when the inference stack can enforce it directly.

## Practical Implications

- multi-image context should be normal when single-frame reasoning is weak
- grounding is a first-class capability, not a separate afterthought
- local and remote models may both participate in one observation pipeline
- the runtime contract should stay stable even if specific model providers change

## What This Document Does Not Claim

This document does not claim that the current repo already implements a complete observation stack. It defines the contract shape that a re-earned runtime should be built against.
