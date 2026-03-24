# AGENTS.md

This file is the mandatory starting point.

## Docs Are the Agent Knowledge Layer

The `docs/` tree is project memory for the agent. It is not primarily end-user documentation. It exists to preserve architecture, constraints, operating assumptions, historical context, and open questions in a form that can be retrieved reliably across sessions.

## Read This First

1. [CLAUDE.md](CLAUDE.md)
2. [repo-status.md](docs/project/repo-status.md)
3. [architecture-overview.md](docs/architecture/architecture-overview.md)
4. [rebuild-interview.md](docs/plans/rebuild-interview.md)
5. [north-star.md](docs/project/north-star.md)

## Retained Domains

Only two documentation domains remain explicit:

- `ALS` — ALAS as reference system, corpus source, and operational comparison point
- `RES` — research, investigations, synthesis, and technical hypotheses

Everything else in `docs/` is organized as a knowledge bucket rather than a domain.

## Knowledge Buckets

- `project/` — repo status, north star, testing posture
- `architecture/` — architecture map and organizing principles
- `workflows/` — assignment and workflow inventories
- `prework/` — corpus work, labeling, extraction, and data gathering before a live runtime
- `runtime/` — future live-system contracts and retained runtime design knowledge
- `vlm/` — model profiles, task contracts, prompt policy, and multimodal design
- `plans/` — active and historical planning documents
- `decisions/` — ADRs and project decisions

## Current Working Reality

As of 2026-03-24:

- active code is still narrow and data-first
- the ALAS log plus screenshot corpus workflow remains real and important
- `scripts/vlm_detector.py` is an offline labeling and analysis tool, not live runtime truth
- `quarantine/` holds code retained for possible salvage, not supported operation
- historical `OBS/NAV/EXE/AUT` naming is preserved only as context inside migrated docs

## Active Code Surface

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

## Vendor Stance

`vendor/AzurLaneAutoScript/` remains intact.

ALAS is used as:

- reference architecture
- corpus source material
- evidence of workflow complexity
- a comparison point for what a mature automation system actually has to solve

ALAS is not the repo's shipped runtime.
