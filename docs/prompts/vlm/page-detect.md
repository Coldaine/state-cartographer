# VLM Prompt Spec: Page Detect

**Primary use:** Corpus labeling, offline adjudication. Not trusted runtime truth.

---

## Current Running Prompts (vlm_detector.py as of 2026-03-23)

The code currently uses these simpler templates (not the full designed API below):

**System prompt:**
```
You are analyzing screenshots from the mobile game Azur Lane (English version, 1280x720).
Answer concisely and precisely. Do not explain.
```

**User prompt template (`_PAGE_DETECT_TMPL`):**
```
Which of the following Azur Lane screens is shown?

{pages}

Reply with ONLY the exact identifier from the list above (e.g. page_main).
If the screen matches none of them, reply: page_unknown
```
where `{pages}` = newline-separated list from `examples/azur-lane/graph.json → states` keys.

**Output:** a single token from the pages list, or `page_unknown`. No confidence score. No rationale.

**Known gaps vs. designed API below:**
- No candidate labels (always sends the full page list)
- No task context
- No neighboring frames
- No structured JSON output — plain text token only
- Fuzzy substring match as fallback

---

## Designed API (target — not yet implemented)

## Purpose

Classify one screenshot or a small screenshot set into one of a caller-provided set of candidate labels.

This prompt is for offline labeling and adjudication, not live runtime truth.

## Exact Inputs Passed

Template:

```text
Label the screenshot set.

Task context: {task_context}
Candidate labels: {candidate_labels}

Return JSON with:
- label: the best candidate label
- confidence: float from 0.0 to 1.0
- rationale: short explanation grounded in visible evidence
- uncertainty_flags: list of short strings
- recommended_followups: list of short strings
```

Images passed:

- one required primary screenshot
- zero or more neighboring frames
- zero or more exemplar frames

## Output Contract

JSON object with:

- `label`
- `confidence`
- `rationale`
- `uncertainty_flags`
- `recommended_followups`

## Example

Candidate labels might be:

```json
["commission_list", "commission_reward", "popup_confirm", "unknown"]
```

## Known Failure Modes

- choosing the nearest-looking label when the correct answer is `unknown`
- failing to use temporal context from neighboring frames
- confusion when candidate labels are too broad or semantically overloaded

## When To Use Multi-Image Or Extra Context

Default to multi-image classification when:

- the page is part of a task-local subflow
- overlays or popups may hide the base page
- the label set includes visually similar substates
- you have preceding or following frames available
