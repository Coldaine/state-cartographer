# OBS — Observation

**Status: Active development (March 2026)**

Observation answers: "what is on screen right now?" Everything involved in capturing, classifying, and learning from screenshots.

## Build order

This is Layer 1 — everything else depends on it. You can't navigate without knowing where you are. You can't execute without confirming arrival.

## What it covers

- Screenshot capture from the emulator (ADB, DroidCast, ATX agent, uiautomator2)
- VLM-based page classification (tiered: always-on small model + on-demand large model)
- Pixel-anchor state detection (locate.py, the fast path)
- Corpus management (raw_stream, labeling, deduplication, black frame cleanup)
- Calibration (learning anchors from labeled corpus)
- Progressive determinism — promoting vision-detected patterns to cheap deterministic checks

## Vision tiers

| Tier | Model | Purpose | Latency | Cost |
|------|-------|---------|---------|------|
| Frontier LLM | Claude (API) | Architect, supervisor, decision-maker | seconds | expensive |
| Large local VLM | Qwen3.5-9B-AWQ (localhost:18900) | On-demand deep analysis, element location, replay analysis | 2-5s | free |
| Small local VLM | Qwen3.5-2B or 0.8B (planned) | Always-on state classifier, feeds state stream | <1s | free |
| Pixel anchors | locate.py | Fast deterministic check when calibrated | <10ms | free |
| ALAS template matching | ALAS internal | Reference labels, not our detection path | ~100ms | free |

## What exists today

- `scripts/locate.py` — pixel-anchor classifier (works against mocks, untested live)
- `scripts/observe.py` — observation extractor from screenshots
- `scripts/vlm_detector.py` — VLM page detection via Qwen3.5-9B (working, thinking mode fixed)
- `scripts/calibrate.py` — single-screenshot anchor calibration
- `scripts/calibrate_from_corpus.py` — batch anchor learning from labeled corpus
- `scripts/label_raw_stream.py` — ALAS log timestamp join for corpus labeling
- `scripts/delete_black_frames.py` — corpus cleanup
- `scripts/screenshot_dedupe.py` — perceptual hash deduplication
- `scripts/state_enumeration_score.py` — detection coverage scoring
- `scripts/pilot_bridge.py` — DroidCast/ATX screenshot capture for MEmu
- `scripts/adb_bridge.py` — raw ADB screenshot fallback

## What's missing

- VLM fallback when pixel anchors fail (locate.py and vlm_detector.py are disconnected)
- Always-on small VLM classifier (model selected, not yet serving)
- Combined ALAS log + VLM labels on the time axis (the merged timeline)
- Online calibration from live runs (only offline corpus calibration exists)
- Mechanism for progressive determinism (tracking which states need vision vs which are stable)
- Fuzzy/tolerant pixel matching (current: exact RGB only)

## Open questions

- How does the system decide pixel anchors vs VLM? Fallback chain or confidence-weighted?
- What triggers recalibration when the game updates its UI?
- Should graph.json store both pixel anchors and VLM-learned anchors?
- Token budget for the always-on classifier — how many frames per second can it sustain?

## Key scripts

| Script | Lines | What it does |
|--------|-------|-------------|
| locate.py | ~320 | Passive state classification from pixel anchors |
| vlm_detector.py | ~275 | VLM-based page detection and element location |
| observe.py | ~100 | Extract observations from a screenshot |
| calibrate_from_corpus.py | ~280 | Learn pixel anchors from labeled screenshot corpus |
| label_raw_stream.py | ~180 | Label screenshots by joining with ALAS log timestamps |
| pilot_bridge.py | ~575 | DroidCast/ATX screenshot capture and emulator control |
