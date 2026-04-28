# Prompt Justification Registry

> **Why this document exists:** Every prompt injected into an agent, VLM, or LLM call in this project must have explicit, documented justification for why it was written the way it was. This document is the canonical source of that justification. It exists to support code review: any reviewer (human or automated) can check a prompt against this registry to verify that the prompt's design decisions are intentional and grounded.
> **For code reviewers:** When reviewing a PR that adds or modifies a prompt, check this file. If the prompt is not documented here, the PR is incomplete. If the justification has drifted from the implementation, flag it.

---

## Prompt Inventory

### VLM Task Prompts (Corpus Labeling)

**Location:** `scripts/vlm_detector.py` (inline constants: `PAGE_DETECT_PROMPT`, `ELEMENT_LOCATE_PROMPT`)
**Standalone file:** `docs/vlm/VLM-task-contracts.md` (schema definitions), `docs/vlm/VLM-prompts.md` (prompt-layer guidance)

| Prompt | Purpose | Key Design Decisions |
|--------|---------|---------------------|
| `PAGE_DETECT_PROMPT` | Classify a screenshot into one of N candidate page labels | Uses candidate label list (not open-ended) to constrain the output space. Requires `confidence` and `uncertainty_flags` to support downstream adjudication. JSON-only output enforced via system prompt. |
| `ELEMENT_LOCATE_PROMPT` | Find a named UI element and return its bounding box | Returns `found: boolean` + `bbox` to distinguish "not found" from "found but low confidence." `recommended_followups` field lets the model suggest what to try next if the element is ambiguous. |

**Detailed justification:** [vlm-detector.md](vlm-detector.md) (per-clause breakdown)

**Why inline constants:** see [vlm-detector.md](vlm-detector.md) "Why Some Schema Content Still Lives In The Prompt" section.

### Kimi Review Prompts

**Location:** `scripts/kimi_review.py` (inline constant: `VISIBLE_ONLY_PROMPT`)
**Detailed justification:** [kimi-review.md](kimi-review.md) (per-clause breakdown)

| Prompt | Purpose | Key Design Decisions |
|--------|---------|---------------------|
| `VISIBLE_ONLY_PROMPT` | Constrain Kimi to only report what is visually present in the screenshot | Prevents hallucination by forcing the model to ground all claims in visible evidence. Used as a secondary/adjudication model in corpus sweep Pass 3. |

**Why Kimi as secondary:** Kimi (Moonshot) is a cheap, capable vision model used for disagreement adjudication. When the primary VLM and Kimi disagree on a page label, the disagreement is logged for manual review.

### Census Extraction Prompts

**Location:** `scripts/census_extract.py` (inline constants: `GRID_EXTRACT_PROMPT`, `DETAIL_EXTRACT_PROMPT`, `GEAR_EXTRACT_PROMPT`)
**Detailed justification:** [census-extract.md](census-extract.md) (per-clause breakdown)

| Prompt | Purpose | Key Design Decisions |
|--------|---------|---------------------|
| `GRID_EXTRACT_PROMPT` | Extract ship name, level, rarity, class from a dock grid screenshot | Lists exact fields to extract. Instructs "include EVERY ship visible, even if partially cut off" to avoid data loss at scroll overlap boundaries. Uses `null` for unreadable fields rather than omitting them. |
| `DETAIL_EXTRACT_PROMPT` | Extract full ship profile from a detail view screenshot | Requests structured nested JSON (`stats: {...}`, `skills: [...]`) because these are variable-length data. `null` policy same as grid. |
| `GEAR_EXTRACT_PROMPT` | Extract equipment from a gear view screenshot | Explicitly asks for empty slots (`"name": null`) so the extraction pipeline can distinguish "no gear" from "extraction failed." Slot numbering (1-6 + "augment") matches the game's UI layout. |

**Why inline (for now):** see [census-extract.md](census-extract.md) for full rationale on inline placement during active development.

---

## Prompt Design Principles

These apply to all prompts in this project:

1. **JSON-only output.** Every prompt that feeds into code must produce parseable JSON. Free-text is only acceptable for human-readable reports.

2. **Null over omission.** Prompts should instruct the model to return `null` for fields it cannot determine, not omit the field. This makes extraction failures visible.

3. **Confidence is mandatory.** Any classification or detection prompt must include a `confidence` field (0.0-1.0) in the output schema. This supports downstream adjudication and progressive determinism.

4. **Candidate-constrained where possible.** When the output space is known (e.g., page labels), provide the candidates explicitly rather than letting the model free-generate. Reduces hallucination.

5. **Grounded rationale.** Prompts should request a `rationale` field that cites visible evidence. This makes VLM reasoning inspectable and supports debugging.

6. **System prompt is structural, not behavioral.** The system prompt sets output format and strictness. Behavioral instructions (what to look for, how to interpret) go in the user prompt.

---

## Adding a New Prompt

When adding a new prompt to this project:

1. Define the task contract first (`docs/vlm/VLM-task-contracts.md` or a new contract doc).
2. Write the prompt — inline in the script is fine during development.
3. Add an entry to this justification registry with: location, purpose, and key design decisions.
4. Once the prompt stabilizes, extract to a standalone file under `docs/prompts/`.
5. Update this registry with the standalone file path.
