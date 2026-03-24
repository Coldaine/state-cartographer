# CLAUDE.md

## Current Working Contract

This repository is no longer pretending to be a live runtime.

The active mission is narrower:

- preserve the ALAS log plus screenshot corpus workflow
- improve corpus hygiene
- support offline VLM-based labeling and adjudication
- document the rebuild questions before adding new runtime code

## Hard Rules

1. Do not add new executor, scheduler, graph, navigation, or resource-management scaffolding until the rebuild interview in `docs/rebuild/INTERVIEW.md` has been resolved into explicit contracts.
2. Do not describe quarantined or deleted code as if it were supported.
3. Every surviving prompt template must have its own markdown spec under `docs/prompts/vlm/`.
4. The default use of `scripts/vlm_detector.py` is offline labeling or adjudication, not runtime truth.
5. The default use of this repo is data work, not emulator control.

## Active Surfaces

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

## Prompt Documentation

Every prompt used by `vlm_detector.py` is documented separately:

- [system-classifier.md](docs/prompts/vlm/system-classifier.md)
- [page-detect.md](docs/prompts/vlm/page-detect.md)
- [element-locate.md](docs/prompts/vlm/element-locate.md)

If a prompt changes materially, update its doc in the same change.

## Quarantine Rule

`quarantine/scripts/pilot_bridge.py` is retained only as unverified environment knowledge.

It is not a supported capture/control path.

## Testing Rule

Only run targeted checks for active code:

- label generation from ALAS logs
- screenshot dedupe
- black-frame detection
- VLM detector smoke checks against the configured endpoint shape
