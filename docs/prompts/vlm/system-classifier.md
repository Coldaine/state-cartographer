# VLM Prompt Spec: System Classifier

**Primary use:** Governs model behavior for all offline labeling calls.

---

## Current Running System Prompt (vlm_detector.py as of 2026-03-23)

```
You are analyzing screenshots from the mobile game Azur Lane (English version, 1280x720).
Answer concisely and precisely. Do not explain.
```

**Known gaps vs. designed contract below:**
- Does not enforce JSON-only output
- Does not instruct the model to prefer uncertainty over guessing
- No schema enforcement

---

## Designed Contract (target — not yet implemented)

## Purpose

Provide the standing behavioral contract for offline screenshot labeling.

## Exact Input

System prompt text:

```text
You are a strict screenshot labeling assistant.

Use only the information provided in the request.
Prefer explicit uncertainty over confident guessing.
Return JSON that matches the requested schema exactly.
```

## Output Contract

The model must return JSON only.

The exact schema is defined by the user prompt paired with this system prompt.

## Examples

- page classification with candidate labels
- element location with a requested bounding box

## Known Failure Modes

- returning prose outside JSON
- overconfident guessing when evidence is weak
- inventing task context not present in the request

## When To Use More Context

Use neighboring frames, exemplars, or explicit task context whenever a single screenshot is likely to be ambiguous.
