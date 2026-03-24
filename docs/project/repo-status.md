# Repo Status

> Historical note: this document was previously `docs/REPO_STATUS.md`.

## Current State

As of 2026-03-24, the repo is still in a data-first rebuild posture.

The active code surface is small. The trusted workflow is centered on:

1. ALAS logs and screenshots
2. corpus alignment and hygiene
3. offline VLM labeling and adjudication
4. documenting what must be true before a live runtime is rebuilt

## Repo Labels

### `active`

Trusted code used now:

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

### `quarantine`

Retained but unsupported:

- `quarantine/scripts/pilot_bridge.py`
- quarantined agents, commands, and legacy tests

### `data`

Source-of-truth assets and corpora:

- `data/**`
- ALAS logs
- screenshot corpora
- labels and prompt outputs

### `vendor`

External reference code:

- `vendor/AzurLaneAutoScript/`

## Knowledge Status By Bucket

- `ALS-reference/`: active and still useful
- `RES-research/`: active and still useful
- `prework/`: active knowledge area; code is still mostly script-shaped
- `vlm/`: active knowledge area; contracts are being clarified
- `runtime/`: knowledge retained, code not yet re-earned
- `workflows/`: active and important, especially for assignment complexity

## Important Constraint

Historical docs may describe runtime, navigation, or backend behavior that is no longer supported by the current codebase. Treat plans and older runtime material as design knowledge unless the corresponding code has been explicitly re-earned.
