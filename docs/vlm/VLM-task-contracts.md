# VLM Task Contracts

## Purpose

This document defines the tasks the repo asks multimodal models to perform.

Task contracts own:

- required inputs
- allowed optional inputs
- expected outputs
- output field meanings
- example result shapes

They do not own backend configuration or general prompt policy.

See also:
- [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md)
- [VLM-model-profiles.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-model-profiles.md)
- [VLM-prompts.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-prompts.md)

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
- `rationale`

Example:

```json
{
  "label": "commission_list_urgent",
  "confidence": 0.81,
  "uncertainty_flags": ["small_text", "partial_occlusion"],
  "rationale": "Urgent tab highlight and commission card layout match the urgent list view."
}
```

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
- `rationale`

Example:

```json
{
  "found": true,
  "bbox": [1042, 611, 1176, 676],
  "confidence": 0.88,
  "rationale": "The blue confirm button matching the target description appears in the lower-right region."
}
```

### `compare_frames`

Use when the question is about change over time.

Inputs:

- at least two ordered frames
- optional task context
- explicit comparison question

Outputs:

- `change_summary`
- `salient_differences`
- `confidence`
- `uncertainty_flags`

Example:

```json
{
  "change_summary": "Popup dismissed; underlying commission list is visible.",
  "salient_differences": [
    "confirm dialog no longer present",
    "list cards visible in center panel"
  ],
  "confidence": 0.84,
  "uncertainty_flags": []
}
```

### `adjudicate_candidates`

Use when one model or pipeline path has already produced candidate interpretations.

Inputs:

- prior candidates or model outputs
- supporting frames
- task context
- adjudication question

Outputs:

- `selected`
- `ranked_candidates`
- `disagreement_notes`
- `follow_up`

Example:

```json
{
  "selected": "reward_popup",
  "ranked_candidates": ["reward_popup", "commission_complete_overlay"],
  "disagreement_notes": "Primary disagreement is whether the dimmed background indicates modal reward collection or commission completion.",
  "follow_up": "Use neighboring frame after confirm-button press if available."
}
```

## Contract Rules

- Task contracts define work shape and output schema.
- Prompts may reference these tasks, but prompts do not replace them.
- Profiles configure how the task is executed; they do not redefine the task.
