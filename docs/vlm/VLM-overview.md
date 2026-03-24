# VLM Overview

> Historical note: this bucket consolidates material that was previously scattered across observation docs and split prompt docs.

## Purpose

`docs/vlm/` defines how this repo uses multimodal models.

This bucket is for capability framing and contract boundaries, not for pretending a live runtime already exists.

See also:
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md)
- [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md)
- [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md)
- [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md)

## What VLM Is For Here

VLM support is used for tasks such as:

- substate classification
- OCR-heavy extraction
- UI element grounding
- frame comparison
- disagreement adjudication
- workflow-context reasoning when deterministic logic is not enough

## Current Reality

The active code surface is still limited.

- `scripts/vlm_detector.py` is an offline labeling/adjudication tool
- the repo does not yet have a fully re-earned live VLM runtime path
- model/task boundaries are being made explicit in docs before they are trusted in runtime code

## Design Direction

The intended split is:

- local multimodal models for frequent, cheap, context-rich work
- stronger remote models for adjudication and harder reasoning

The intended defaults are:

- multi-image context when ambiguity requires it
- explicit task contracts
- explicit model profiles
- thin prompt text
- policy in config/contracts rather than in prose

## Document Map

- [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md)
  - backend/model capability configuration
- [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md)
  - task schemas, expected inputs, and outputs
- [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md)
  - prompt-layer guidance only
