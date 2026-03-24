# VLM Model Profiles

## Purpose

A model profile defines backend behavior and capability assumptions.

It is configuration and capability metadata, not prompt text and not task schema.

See also:
- [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md)
- [VLM-task-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-task-contracts.md)
- [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md)

## What A Profile Owns

A usable profile should define at least:

- backend type
- endpoint or transport
- model identifier
- structured output mode
- reasoning mode or thinking policy
- image-count / context-window limits
- grounding support
- OCR support
- expected role in the pipeline
- fallback / adjudication role

## Example Profile Shape

```yaml
profile_id: qwen-local-default
backend: openai_compatible_local
model: qwen-vl-local
structured_output: json_schema
reasoning_mode: low
max_images: 6
grounding: true
ocr: strong
role: primary_classifier
fallback_role: none
```

## Current Working Profiles

### Local profile

**Intended family:** local Qwen multimodal deployment

Default role:

- frequent offline labeling
- grounding and OCR-heavy tasks
- candidate narrowing
- sequence-aware comparison when latency matters

Expected strengths:

- local availability
- lower marginal cost
- multi-image context
- structured outputs when configured correctly

### Remote profile

**Intended family:** remote Nemotron-class multimodal profile

Default role:

- adjudication on hard cases
- higher-cost reasoning over ambiguous sequences
- disagreement resolution
- difficult extraction tasks where local confidence is weak

Expected strengths:

- stronger reasoning budget
- better tie-breaking and synthesis
- useful second opinion for corpus review

## Boundary Rules

- Structured output enforcement belongs here and in backend/API configuration.
- Image-count limits belong here, not in prompt prose.
- Reasoning policy belongs here, not in prompt prose.
- Backend selection belongs here, not in task contracts.
