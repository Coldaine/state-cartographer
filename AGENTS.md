# AGENTS.md

This file is the mandatory starting point.

## Current Phase

As of 2026-03-23, this repo is in a data-first peel-back phase.

The old runtime/navigation surface has been removed from active code. This repo now preserves truth sources and a minimal set of tools around the ALAS log plus screenshot corpus workflow.

## Read This First

1. [CLAUDE.md](CLAUDE.md)
2. [docs/REPO_STATUS.md](docs/REPO_STATUS.md)
3. [docs/rebuild/INTERVIEW.md](docs/rebuild/INTERVIEW.md)

## Repo Labels

- `active`: trusted code used right now
- `quarantine`: retained for possible future salvage, not trusted or supported
- `data`: preserved truth and already-paid-for artifacts
- `vendor`: external reference code and corpus source material

## What Is Active

Active code is intentionally narrow:

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

These tools exist to support:

- alignment between ALAS logs and screenshot corpus artifacts
- corpus hygiene
- offline VLM labeling, adjudication, and analysis

## What Is Not Active

There is no supported live runtime entrypoint in this repo right now.

The following lines of work were removed from active code during the peel-back:

- executor and scheduler scaffolding
- graph/navigation scaffolding
- anchor calibration and mock runtime side paths
- one-off analysis utilities that were not required by the corpus pipeline

Do not treat historical docs or example artifacts as proof that a runtime exists.

## Vendor Stance

`vendor/AzurLaneAutoScript/` is preserved intact.

ALAS remains useful as:

- reference implementation
- corpus source material
- operational truth about workflow complexity

ALAS is not the runtime being shipped from this repo.

## Quarantine

Environment-specific capture/control experiments are retained only under [quarantine/README.md](quarantine/README.md).

Anything under `quarantine/` is out of the supported path unless it is explicitly re-earned.
