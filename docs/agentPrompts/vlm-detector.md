# VLM Detector Prompts

## Code Link

- [scripts/vlm_detector.py](/mnt/d/_projects/MasterStateMachine/scripts/vlm_detector.py)

## Purpose

This document explains the prompt text embedded in `vlm_detector.py` and how each prompt block is intended to support offline labeling and adjudication.

This tool is for offline corpus work, not live runtime control.

## Prompt Families In This File

`vlm_detector.py` contains three prompt blocks:

- `SYSTEM_PROMPT`
- `PAGE_DETECT_PROMPT`
- `ELEMENT_LOCATE_PROMPT`

## `SYSTEM_PROMPT`

### Role Statement

`You are a strict screenshot labeling assistant.`

Why it exists:
- narrows the model role to evidence extraction and labeling

How it helps:
- reduces conversational drift
- frames the call as a constrained classification/grounding task instead of an open assistant interaction

### Evidence Constraint

`Use only the information provided in the request.`

Why it exists:
- blocks outside assumptions and repo-memory leakage

How it helps:
- keeps the model tied to the image set and supplied context
- reduces invented workflow claims

### Uncertainty Preference

`Prefer explicit uncertainty over confident guessing.`

Why it exists:
- offline labeling is harmed more by polished false certainty than by nulls

How it helps:
- biases the model toward surfacing ambiguity rather than forcing a claim

### Exact-JSON Rule

`Return JSON that matches the requested schema exactly.`

Why it exists:
- the caller expects structured output

How it helps:
- increases compatibility with downstream parsing
- complements the API-side `response_format` constraint

## `PAGE_DETECT_PROMPT`

### Task Framing

`Label the screenshot set.`

Why it exists:
- defines the task as candidate-based labeling over one or more images

How it helps:
- makes multi-image context legitimate
- keeps the model on classification rather than generic description

### Task Context

`Task context: {task_context}`

Why it exists:
- some page identities are easier to resolve when the workflow family is known

How it helps:
- helps the model focus on relevant UI cues when the context is concrete

Risk:
- bad task context can bias the answer

### Candidate Labels

`Candidate labels: {candidate_labels}`

Why it exists:
- bounds the decision space

How it helps:
- reduces ontology drift
- turns the problem into closed-set selection rather than free-form naming

### Output Fields

The prompt asks for:

- `label`
- `confidence`
- `rationale`
- `uncertainty_flags`
- `recommended_followups`

Why they exist:
- `label` gives the provisional classification
- `confidence` makes uncertainty explicit
- `rationale` exposes evidence
- `uncertainty_flags` makes ambiguity machine-readable
- `recommended_followups` supports offline review and adjudication

How they help:
- keep the output usable for corpus review rather than just top-1 guessing

## `ELEMENT_LOCATE_PROMPT`

### Task Framing

`Locate the requested UI element in the screenshot set.`

Why it exists:
- defines the task as grounding, not classification

How it helps:
- focuses the model on target-finding behavior

### Target Element

`Target element: {target}`

Why it exists:
- the grounding target must be explicit

How it helps:
- gives the model a direct visual query to anchor on

### Task Context

`Task context: {task_context}`

Why it exists:
- some UI elements are ambiguous without workflow context

How it helps:
- helps disambiguate visually similar controls when the context is good

### Output Fields

The prompt asks for:

- `found`
- `confidence`
- `rationale`
- `bbox`
- `recommended_followups`

Why they exist:
- `found` allows explicit absence
- `confidence` expresses uncertainty
- `rationale` exposes the evidence basis
- `bbox` provides the usable grounding result
- `recommended_followups` supports offline review when the result is weak

How they help:
- turn the response into a reviewable grounding artifact rather than just prose

## Why Some Schema Content Still Lives In The Prompt

At the architecture level, schema and output policy should live outside prompts where possible.

In this file, the field lists still appear in the prompt because:

- local and remote VLMs may drift if the expected fields are only implied
- the tool is meant for offline review workflows where explicit field reminders improve consistency

This is a pragmatic compromise, not a claim that prompt text should own the entire contract.
