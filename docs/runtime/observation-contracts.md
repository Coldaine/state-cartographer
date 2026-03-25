# Observation Contracts

## Purpose

What the runtime must be able to ask of observation, regardless of which models or retrieval strategies are in use.

## Core Runtime Questions

The runtime needs answers to:
- What is visible right now?
- What workflow substate is this?
- What changed between the last frame and this one?
- Where is the element I need to act on?
- How uncertain is this answer?

## Required Inputs

Observation calls use more than a single screenshot when needed:
- Primary frame
- Optional neighboring frames
- Optional task or workflow context
- Optional candidate labels or retrieved exemplars
- Session context when available

## Required Outputs

Observation returns structured results:
- Classification result or candidate set
- Confidence and uncertainty
- Grounding result (bbox, point, or not found)
- Evidence summary grounded in visible content
- Follow-up recommendation when evidence is weak

## Contract Boundaries

- Model configuration belongs in profiles (see [VLM-model-profiles.md](../vlm/VLM-model-profiles.md))
- Task schema belongs in task contracts (see [VLM-task-contracts.md](../vlm/VLM-task-contracts.md))
- Prompt wording is the thinnest layer (see [VLM-prompts.md](../vlm/VLM-prompts.md))
- Runtime consumes typed outputs, not raw model strings

## Practical Implications

- Multi-image context is normal when single-frame reasoning is weak
- Grounding is first-class, not an afterthought
- Local and remote models may both participate in one observation pipeline
- The runtime contract stays stable even if model providers change
