# VLM Prompt Spec: Element Locate

**Primary use:** Corpus annotation, offline element grounding. Not trusted runtime tap-target truth.

---

## Current Running Prompts (vlm_detector.py as of 2026-03-23)

The code currently uses a simpler template:

**User prompt template (`_LOCATE_TMPL`):**
```
In this 1280x720 Azur Lane screenshot, find: {description}

Reply with ONLY the pixel coordinates in the format:  x,y
If the element is not visible, reply: not_visible
```

**Output:** `x,y` coordinate pair or `not_visible`. No bounding box. No confidence. No rationale.

**Known gaps vs. designed API below:**
- Returns a point, not a bounding box
- No confidence or rationale
- Single image only
- Regex-parsed from raw text (fragile)

---

## Designed API (target — not yet implemented)

## Purpose

Locate a requested UI element or visual cue inside one screenshot or a small screenshot set.

## Exact Inputs Passed

Template:

```text
Locate the requested UI element in the screenshot set.

Target element: {target}
Task context: {task_context}

Return JSON with:
- found: boolean
- confidence: float from 0.0 to 1.0
- rationale: short explanation grounded in visible evidence
- bbox: [x1, y1, x2, y2] or null
- recommended_followups: list of short strings
```

Images passed:

- one required primary screenshot
- zero or more neighboring frames
- zero or more exemplar frames

## Output Contract

JSON object with:

- `found`
- `confidence`
- `rationale`
- `bbox`
- `recommended_followups`

## Example

Target element examples:

- `collect reward button`
- `commission tab`
- `dismiss popup close control`

## Known Failure Modes

- returning a bounding box for a semantic region rather than the actual target
- failing to express uncertainty when the element is partially occluded
- confusing similar controls without task context

## When To Use More Context

Use neighboring frames or exemplars when:

- the target appears only briefly
- animations obscure the target
- multiple similar controls appear in one screenshot
