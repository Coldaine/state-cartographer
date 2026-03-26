# Plan: VLM Corpus Sweep

## Goal

Run the screenshot corpus through multiple vision models to produce a labeled state vocabulary and transition table — the raw material for the state machine. This replaces exhaustive manual review with automated multi-pass labeling and targeted human adjudication.

## Why This Exists

The previous approach (manual "golden stretch" review, one ledger row at a time) produced 1 reviewed row in two weeks. At that rate the state machine would take months. Meanwhile, ALAS runs daily and the game updates regularly.

The insight (March 20, 2026): ALAS log labels are **task-context labels** ("page_reward" means the Reward task is active), not **visual labels** (what's actually on screen). The VLM gives visual truth. Merging VLM labels with ALAS log events on the time axis produces the combined narrative needed to extract the state graph.

## Data Available

- ~4000 screenshots in `data/raw_stream/` (filename = timestamp)
- ALAS logs in `vendor/AzurLaneAutoScript/log/` (timestamped text)
- 1 reviewed stretch in `data/review/reviewed_stretches.tsv`
- ALAS source code with all page definitions and button coordinates in `vendor/AzurLaneAutoScript/module/ui/page.py` and assets

## Pipeline

### Pass 1: Cheap VLM bulk label

Run every screenshot through a small local VLM (Qwen 2B or similar via llama-swap at `localhost:18900`).

For each frame, produce:
```json
{
  "file": "20260320_002241_384.png",
  "label": "commission_list_urgent",
  "confidence": 0.82,
  "visible_text": ["Urgent", "Commission", "00:32:15"],
  "visible_regions": ["tab_bar", "commission_cards", "header_nav"],
  "rationale": "Urgent tab highlighted, commission cards visible"
}
```

Use `scripts/vlm_detector.py` `detect_page` with a candidate label set derived from ALAS page names. The VLM client already supports this.

### Pass 2: ALAS log alignment

Parse ALAS logs and align by timestamp to the VLM labels from Pass 1.

For each frame, merge:
- **VLM label** (what's visible)
- **ALAS task context** (what task was running)
- **ALAS page label** (what ALAS thought the page was)
- **ALAS action** (what ALAS did next — tap coordinates, page switch, etc.)

Output: a combined timeline where each row has both visual truth and action context.

### Pass 3: Disagreement sweep

Filter the merged timeline for rows where VLM label != ALAS page label. These are the interesting cases:
- ALAS says "page_reward" but screen shows commission list
- ALAS says "unknown" but VLM confidently labels the page
- VLM confidence is low (< 0.6) — genuinely ambiguous screens

Run these disagreement frames through a **second model** (Kimi via `scripts/kimi_review.py`, or the 9B Qwen model) for adjudication. Two models agreeing against ALAS = high confidence the VLM is right.

### Pass 4: Triple extraction

From the cleaned merged timeline, extract **(source_page, action, target_page)** triples:
- Look for consecutive frames where the label changes
- The ALAS action log tells you what caused the transition (tap at coordinates, swipe, back button, etc.)
- Each triple becomes an edge in the state graph

### Output Artifacts

1. **State vocabulary** — canonical visual page names with example frames
2. **Transition table** — directed edges with action type and coordinates
3. **Confidence map** — which states the VLM handles well vs poorly
4. **Disagreement log** — cases where models disagree, for human review
5. **Recovery patterns** — how the game returns from unknown/error states

These feed directly into `state_machine_v0`: states + transitions + guards.

## What's Needed to Execute

| Need | Status |
|---|---|
| Working screenshot capture | Done (Vulkan + ADB) |
| VLM client | Done (`scripts/vlm_detector.py`) |
| Local model serving | Done (llama-swap at localhost:18900) |
| Kimi adjudication client | Done (`scripts/kimi_review.py`) |
| Candidate label set | Derivable from ALAS `page.py` — ~43 page names |
| ALAS log parser | Needs writing — parse timestamped log lines |
| Timeline merger | Needs writing — join VLM labels + ALAS events by timestamp |
| Triple extractor | Needs writing — detect label transitions in timeline |

## Execution Order

1. Derive candidate label set from ALAS page definitions
2. Run Pass 1 (bulk VLM label) — can batch ~20 frames per call
3. Write ALAS log parser, run Pass 2 (alignment)
4. Run Pass 3 (disagreement adjudication) on filtered subset
5. Run Pass 4 (triple extraction)
6. Review output artifacts, publish `state_machine_v0`

## Constraints

- VLM calls are ~1-5s each. ~4000 frames at 20 per batch = ~200 calls = ~15 minutes
- Kimi adjudication is slower and costs money — only run on disagreements (~5-10% of frames)
- ALAS logs may not cover all screenshots — some frames have no matching log context
- The candidate label set may need iteration — start with ALAS page names, refine after Pass 1

## See Also

- [VLM-task-contracts.md](../vlm/VLM-task-contracts.md) — task schemas for classification
- [VLM-model-profiles.md](../vlm/VLM-model-profiles.md) — model capabilities
- [corpus-review-playbook.md](../prework/corpus-review-playbook.md) — the manual review approach (still valid for edge cases)
- [RES-founding-synthesis.md](../RES-research/RES-founding-synthesis.md) — the state machine thesis
