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

**Why inline constants:** These prompts are tightly coupled to the `VLMClient.complete()` call that formats and sends them. Extracting to external files would add a file-read step without improving reviewability, since the prompt and the code that uses it are in the same 300-line module. The task contracts doc (`VLM-task-contracts.md`) serves as the standalone specification.

**Why JSON-only output:** The system prompt enforces `Return JSON that matches the requested schema exactly.` because downstream code calls `json.loads()` on the response. Free-text responses would crash the pipeline.

**Why confidence + uncertainty_flags:** Multi-pass corpus sweep (Pass 3) uses confidence to decide which labels need adjudication. Without it, every label would need a second opinion.

### Census Extraction Prompts

**Location:** `scripts/census_extract.py` (inline constants: `GRID_EXTRACT_PROMPT`, `DETAIL_EXTRACT_PROMPT`, `GEAR_EXTRACT_PROMPT`)
**Standalone file:** To be extracted to `docs/prompts/census-extract-prompts.md` when the prompts stabilize after live calibration.

| Prompt | Purpose | Key Design Decisions |
|--------|---------|---------------------|
| `GRID_EXTRACT_PROMPT` | Extract ship name, level, rarity, class from a dock grid screenshot | Lists exact fields to extract. Instructs "include EVERY ship visible, even if partially cut off" to avoid data loss at scroll overlap boundaries. Uses `null` for unreadable fields rather than omitting them. |
| `DETAIL_EXTRACT_PROMPT` | Extract full ship profile from a detail view screenshot | Requests structured nested JSON (`stats: {...}`, `skills: [...]`) because these are variable-length data. `null` policy same as grid. |
| `GEAR_EXTRACT_PROMPT` | Extract equipment from a gear view screenshot | Explicitly asks for empty slots (`"name": null`) so the extraction pipeline can distinguish "no gear" from "extraction failed." Slot numbering (1-6 + "augment") matches the game's UI layout. |

**Why inline (for now):** These prompts are in active development. They will be tested against real dock screenshots and iterated. Once stable, they should be extracted to standalone files under `docs/prompts/`. The current inline placement avoids the overhead of loading external files during rapid iteration.

**Why "include EVERY ship" in grid prompt:** The capture pipeline deliberately overlaps consecutive grid pages by 1-2 rows. The extraction must capture all ships including partial ones so that deduplication (by ship name in SQLite UNIQUE constraint) can reconcile overlaps correctly. Instructing the VLM to skip partial ships would create gaps.

**Why null over omission:** Downstream SQLite COALESCE merge depends on null fields being explicitly present. If a field is omitted from the JSON, `dict.get()` returns `None` which writes NULL to the DB. If a field is absent entirely, the merge logic still works, but explicit null in the prompt output makes the VLM's uncertainty visible in the raw extraction data.

### Navigator Agent Prompt (PR #35, not yet merged)

**Location:** `.github/agents/azur-lane-navigator.agent.md` (standalone file)
**Status:** Under review in PR #35. Has known issues flagged by automated reviewers (self-referencing agent, nonportable session path, drive pattern bugs).

| Prompt Section | Purpose | Key Design Decisions |
|---------------|---------|---------------------|
| Drive Pattern | Canonical observe-act-observe loop for Pilot | Uses `Pilot` context manager. Screenshots saved to `data/` for VLM consumption. Designed to be copy-pasted into interactive agent sessions. |
| Recovery | Handle stuck states and unexpected popups | Back button (57, 55) as universal escape. Health check fallback. Escalation to human if stuck > 3 cycles. |

**Why standalone `.agent.md`:** This is a GitHub Copilot agent definition that must be discoverable by the agent framework. Standalone file is the correct pattern here.

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
