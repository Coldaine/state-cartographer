# Kimi Review Prompt

## Code Link

- [scripts/kimi_review.py](/mnt/d/_projects/MasterStateMachine/scripts/kimi_review.py)

## Purpose

This document explains the prompt used by `kimi_review.py`, why each part exists, and how it is supposed to help the model produce useful cheap-review output for corpus inspection.

This is a first-pass evidence-extraction helper, not a trusted reviewer of record.

## Prompt Scope

The prompt in `kimi_review.py` is intentionally narrow. It is trying to get:

- visible text
- visible regions
- an optional closed-set provisional label
- an explicit confidence value
- ambiguity notes

That scope is meant to support disagreement surfacing before human review.

## Prompt Breakdown

### Opening Instruction

`Inspect the provided screenshot set.`

Why it exists:
- tells the model the unit is a set, not a singleton frame
- permits neighboring frames to act as context

How it helps:
- pushes the model toward cross-frame reading instead of over-indexing on one image

### Fixed JSON Key List

The prompt requires exactly these keys:

- `visible_text`
- `visible_regions`
- `best_label`
- `confidence`
- `ambiguity_notes`

Why it exists:
- keeps output small and predictable
- aligns the response with the cheap-sieve role described in the corpus review docs

How it helps:
- forces the model to separate raw evidence from provisional interpretation
- gives downstream review a compact shape that is easy to compare across frames

### Visible-Only Rule

`use only what is visibly present in the images`

Why it exists:
- prevents workflow priors from becoming fake observations

How it helps:
- reduces hidden-state invention
- keeps the output anchored to screenshot evidence instead of repo lore

### No Hidden-State Inference Rule

`do not infer the next destination, intended task, or hidden state from workflow expectations`

Why it exists:
- this repo has already seen polished but wrong generated labels

How it helps:
- blocks the model from turning temporal expectations into asserted truth
- keeps uncertain cases available for human review instead of laundering guesses

### Closed-Set Label Rule

`if a label set is provided, choose only from that set or return null`

Why it exists:
- reduces ontology drift
- makes the label field usable for provisional comparison without implying trust

How it helps:
- keeps output comparable to a local candidate set
- allows disagreement surfacing without encouraging free-form taxonomy sprawl

### Evidence-First Rule

`evidence first, label second`

Why it exists:
- labels are weaker than visible facts in this workflow

How it helps:
- pushes the model to expose the basis for a label before collapsing to one
- gives a reviewer something to inspect even when the label is wrong

### Task Context Field

`Task context: {task_context}`

Why it exists:
- some review windows are easier to interpret when the active task family is known

How it helps:
- can narrow attention toward the right UI family when the context is concrete and accurate

Risk:
- vague or noisy task context can bias the answer
- this input should stay specific and relevant, or be omitted

### Allowed Labels Field

`Allowed labels: {allowed_labels}`

Why it exists:
- exposes the optional closed set directly in the prompt

How it helps:
- reduces semantically adjacent label drift
- gives the model a bounded decision surface when label comparison matters

## Current Gaps

This prompt is intentionally small, but the current implementation still has meaningful gaps:

- it does not explain how neighboring frames should be used temporally
- it does not distinguish primary image from neighboring images explicitly
- it does not explain what confidence should mean operationally
- it relies on the caller to provide clean task context

Those are implementation-quality issues, not reasons to abandon the cheap-review role.
