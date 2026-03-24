# CLAUDE.md

## Working Contract

Treat `docs/` as the repo's agent knowledge layer.

Only `ALS` and `RES` remain explicit domains. `project`, `architecture`, `workflows`, `prework`, `runtime`, and `vlm` are knowledge buckets, not domains.

## Hard Rules

1. Do not reintroduce `OBS/NAV/EXE/AUT` as active domain labels in the docs tree.
2. Do not let runtime docs claim supported behavior the codebase has not earned.
3. Keep model configuration separate from task contracts and prompt wording in both code and docs.
4. Treat `prework`, `vlm`, and `runtime` as distinct buckets with different purposes.
5. When changing the project understanding, update the relevant docs in the same change.
6. Treat `quarantine/` as unsupported unless a file is explicitly re-earned.

## Current Active Surfaces

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

## Documentation Expectations

- `docs/ALS-reference/` and `docs/RES-research/` are retained domains.
- `docs/vlm/` is the operational home for multimodal model profiles, task contracts, and prompt policy.
- `docs/runtime/` is for live-system contracts and retained runtime design knowledge.
- `docs/prework/` is for corpus and data-building work that happens before or outside the live runtime.

## Testing Rule

Prefer targeted checks only:

- corpus labeling from ALAS logs
- screenshot dedupe and black-frame cleanup behavior
- VLM detector smoke checks and contract tests
- documentation/link checks when docs are moved or consolidated
