# VLM Model Profiles

## Purpose

A model profile defines backend behavior and capability assumptions.

It is not the same thing as a prompt.

## Profile Fields

A usable profile should capture at least:

- backend type and endpoint
- model identifier
- structured output mode
- reasoning mode or thinking policy
- supported image count / context policy
- grounding support
- OCR strength
- expected role in the pipeline

## Current Working Profiles

### Local profile

**Intended model family:** local Qwen 3.5 multimodal deployment

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

**Intended model family:** latest NVIDIA Nemotron remote profile

Default role:

- adjudication on hard cases
- higher-cost reasoning over ambiguous sequences
- disagreement resolution
- difficult extraction tasks where local confidence is weak

Expected strengths:

- stronger reasoning budget
- better tie-breaking and synthesis
- useful second opinion for corpus review

## Important Boundary

If the backend can enforce structured output, that belongs in the profile and API configuration, not in repeated prompt text.
