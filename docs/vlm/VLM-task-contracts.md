# VLM Task Contracts

## Purpose

Define the tasks the repo asks multimodal models to perform, along with the expected inputs and outputs.

## Core Task Types

### `classify_substate`

Use when the goal is to choose among candidate workflow substates.

Inputs:

- primary frame
- optional neighboring frames
- task context
- candidate labels
- optional exemplars

Outputs:

- `label`
- `confidence`
- `uncertainty_flags`
- short evidence-grounded rationale

### `ground_element`

Use when the goal is to find a UI element or visual cue.

Inputs:

- primary frame
- optional neighboring frames
- target description
- optional task context
- optional exemplars

Outputs:

- `found`
- `bbox` or point representation
- `confidence`
- short evidence-grounded rationale

### `compare_frames`

Use when the question is about change over time.

Inputs:

- at least two ordered frames
- optional task context
- explicit comparison question

Outputs:

- change summary
- salient differences
- confidence / uncertainty

### `adjudicate_candidates`

Use when one model or pipeline path has already produced candidate interpretations.

Inputs:

- prior candidates or model outputs
- supporting frames
- task context
- adjudication question

Outputs:

- selected answer or ranked candidates
- disagreement notes
- follow-up recommendation when unresolved

## Contract Rule

Task contracts define the shape of the work. Prompts should not be the only place these contracts live.
