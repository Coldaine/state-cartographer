# Census Extraction Prompts

## Code Link

- [scripts/census_extract.py](../../scripts/census_extract.py)

## Purpose

This document explains the prompt text embedded in `census_extract.py` and how each prompt block is intended to support offline dock census extraction from Azur Lane screenshots.

This tool is for offline census work only.
It is not a live runtime control primitive.

## Prompt Families In This File

`census_extract.py` currently contains four prompt blocks:

- `SYSTEM_PROMPT`
- `GRID_EXTRACT_PROMPT`
- `DETAIL_EXTRACT_PROMPT`
- `GEAR_EXTRACT_PROMPT`

## `SYSTEM_PROMPT`

### Role Statement

`You are a strict screenshot analysis assistant for Azur Lane.`

Why it exists:
- narrows the model role to evidence extraction from game screenshots
- the word "strict" biases the model toward conservative extraction rather than creative interpretation

How it helps:
- prevents hallucination of ships, stats, or gear that are not visible in the image
- grounds all claims in visible evidence

### Evidence Constraint

`Use only the information visible in the provided screenshot.`

Why it exists:
- blocks the model from using training-data knowledge about ship stats, expected gear loadouts, or typical fleet compositions

How it helps:
- ensures extracted data reflects the actual state of the player's dock, not canonical game data
- prevents the model from "correcting" partially visible or unusual values

### Uncertainty Preference

`Prefer explicit uncertainty over confident guessing.`

Why it exists:
- census extraction of tiny text, ambiguous colors, and partially obscured UI is inherently uncertain
- a confident wrong extraction is worse than an explicit null

How it helps:
- biases the model toward null fields rather than plausible guesses
- keeps extraction failures visible in the raw data for downstream review

### Exact-JSON Rule

`Return JSON that matches the requested schema exactly.`

Why it exists:
- downstream code calls `json.loads()` on the response and accesses fields with `dict.get()`

How it helps:
- prevents free-text responses that would crash the pipeline
- complements the API-side `response_format: {"type": "json_object"}` constraint

### Why "strict" appears in the system prompt

The system prompt says "strict screenshot analysis assistant" rather than just "analysis assistant" because:
- the extraction pipeline parses VLM output programmatically
- creative or conversational responses break `json.loads()` and `dict.get()` calls
- "strict" primes the model to follow the schema literally rather than embellish

## `GRID_EXTRACT_PROMPT`

### Task Framing

`Analyze this Azur Lane dock grid screenshot.`

Why it exists:
- tells the model the image type so it knows what visual layout to expect
- dock grid screenshots have a specific card-based layout with name, level, border color, and class icon

How it helps:
- orients the model to look for repeated card elements in a grid arrangement

### Field List

The prompt specifies exactly: `name`, `level`, `rarity`, `ship_class`.

Why it exists:
- these are the fields that the SQLite schema expects
- naming them explicitly prevents the model from inventing extra fields or using different key names

How it helps:
- downstream code parses with `dict.get("name")`, `dict.get("level")`, etc.
- structured JSON with exact field names means no field-name normalization is needed

### Include EVERY Ship Rule

`Include EVERY ship visible, even if partially cut off at edges.`

Why it exists:
- the capture pipeline deliberately overlaps consecutive grid pages by 1-2 rows
- scroll overlap dedup depends on complete extraction from both overlapping pages
- if the VLM skips partially visible ships, those ships may not appear in either page's extraction, creating gaps

How it helps:
- ensures deduplication by ship name (via SQLite UNIQUE constraint) works correctly
- partial ships extracted from one page get their missing fields filled in from the overlapping page via COALESCE merge

### Null Over Omission

`If a field cannot be determined, use null.`

Why it exists:
- downstream SQLite COALESCE merge needs explicit nulls to distinguish "field not visible" from "field not present in response"
- `dict.get()` returns `None` for missing keys, which writes NULL to the DB, but explicit null in the prompt output makes the VLM's uncertainty visible in the raw extraction JSON

How it helps:
- makes extraction failures inspectable in the raw data
- prevents the model from silently omitting fields it is uncertain about

### Confidence Field

`confidence: float 0.0-1.0 indicating how confident you are in the overall extraction`

Why it exists:
- grid screenshots vary widely in quality: some have clear large text, others have tiny text at high zoom-out levels
- extraction of tiny text and ambiguous rarity colors needs a trustworthiness signal

How it helps:
- downstream pipeline can flag low-confidence pages for manual review
- supports progressive determinism: high-confidence extractions proceed automatically, low-confidence ones get human attention

### Rationale Field

`rationale: one sentence explaining what visual evidence you used`

Why it exists:
- makes VLM reasoning inspectable for debugging
- when an extraction is wrong, the rationale reveals whether the model misread text, confused colors, or hallucinated

How it helps:
- supports corpus review workflows where a human inspects extraction quality
- provides an audit trail for each extraction decision

## `DETAIL_EXTRACT_PROMPT`

### Task Framing

`Analyze this Azur Lane ship detail screenshot.`

Why it exists:
- detail view screenshots have a different layout from grid views: a single ship with stats, skills, affinity, and limit break information

How it helps:
- orients the model to look for a single-ship detailed profile rather than a grid of cards

### Extended Field List

The prompt specifies: `name`, `level`, `rarity`, `ship_class`, `affinity`, `stats`, `skills`, `limit_break`.

Why it exists:
- detail views contain richer information than grid views
- `stats` is a nested object (firepower, torpedo, aviation, etc.) because stat counts vary by ship class
- `skills` is an array because ships have 1-4 skills of variable length

How it helps:
- structured nested JSON matches the SQLite schema where stats and skills are stored as `stats_json` and `skills_json` TEXT columns

### Null Repetition

`Use null for any field that cannot be determined.`

Why this phrase is repeated in every prompt:
- defense in depth against free-text responses
- each prompt is sent independently to the VLM; the model does not see the other prompts
- repeating the null instruction in every prompt ensures the model follows the policy regardless of which prompt it receives

### Confidence and Rationale

Same design as `GRID_EXTRACT_PROMPT`. Detail views have their own uncertainty sources: affinity hearts may be partially obscured, skill levels may be in small text, and limit break stars may be ambiguous at low image quality.

## `GEAR_EXTRACT_PROMPT`

### Task Framing

`Analyze this Azur Lane ship equipment/gear screenshot.`

Why it exists:
- gear view screenshots show equipment slots with item names, enhancement levels, and rarity colors

How it helps:
- orients the model to look for a slot-based equipment layout

### Empty Slot Representation

`Include empty slots as {"slot": N, "name": null, "level": null, "rarity": null}.`

Why it exists:
- the extraction pipeline must distinguish "no gear equipped in slot 3" from "extraction failed for slot 3"
- if empty slots are omitted, the pipeline cannot tell whether the VLM skipped the slot or the slot was genuinely empty

How it helps:
- makes the equipment inventory complete and auditable
- downstream code can count equipped vs. empty slots without guessing

### Slot Numbering

`slot number (1-6, or "augment" for augment module)`

Why it exists:
- matches the game's UI layout where ships have 6 main equipment slots plus an optional augment module
- using consistent slot identifiers means equipment records from different extraction runs can be compared

How it helps:
- provides a stable key for slot-level comparison across census runs

### Confidence and Rationale

Same design as the other prompts. Gear views have specific uncertainty sources: enhancement level text (+0 to +13) can be small, and rarity colors for equipment follow a different palette than ship rarity colors.

## Why Inline Constants (For Now)

These prompts are in active development. They will be tested against real dock screenshots and iterated. Once stable, they should be extracted to standalone files under `docs/prompts/`. The current inline placement avoids the overhead of loading external files during rapid iteration.

The prompts are tightly coupled to the `VLMClient.complete()` call that formats and sends them. Extracting to external files would add a file-read step without improving reviewability, since the prompt and the code that uses it are in the same module.

## Why "Use null" Is Repeated In Every Prompt

This is intentional defense in depth. Each prompt is sent to the VLM independently in a separate API call. The model has no memory of previous calls. Repeating the null instruction in every prompt ensures the policy is enforced regardless of which prompt the model receives. Without this repetition, a model that only sees `GEAR_EXTRACT_PROMPT` would have no instruction about null handling.
