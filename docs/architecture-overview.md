# Architecture Overview

> Historical note: this document was previously `docs/architecture.md`. Older `OBS/NAV/EXE/AUT` language is historical context only.

## Purpose

This document explains how the repo is organized as knowledge, not just as code.

See also:
- [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md)
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/project/repo-index.md)
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)

The key distinction is:

- `docs/` organizes agent knowledge
- code and data organize implementation work

Those are different axes and should not be forced into one tree.

## Documentation Domains

Two documentation domains remain explicit because they describe durable bodies of project knowledge independent of current code shape:

- `ALS` — ALAS as reference system, harvested truth source, and operational comparison point
- `RES` — research, experiments, technical hypotheses, and synthesis work

These domains live in:

- `docs/ALS-reference/`
- `docs/RES-research/`

## Knowledge Buckets

Everything else in `docs/` is a knowledge bucket rather than a domain.

| Bucket | Purpose |
|---|---|
| `project/` | current reality, north star, repo indexing, validation posture |
| `architecture-overview.md` | organizing principles and architectural map |
| `workflows/` | assignment and workflow knowledge |
| `prework/` | corpus alignment, cleanup, extraction, and data-gathering programs |
| `runtime/` | live-system contracts and retained runtime design constraints |
| `vlm/` | multimodal model profiles, task contracts, prompt policy |
| `plans/` | tactical and strategic planning documents |
| `decisions/` | ADRs and stable project decisions |

## Code And Data Buckets

The implementation side of the repo should be thought about separately from docs:

- `data/` holds truth artifacts and corpora
- `vendor/` holds external code and reference systems
- `scripts/` is the current active script-shaped surface
- future `prework/`, `vlm/`, and `runtime/` code areas are design directions, not proof of present implementation
- `quarantine/` holds retained but unsupported material

## Why Docs And Code Use Different Axes

The docs tree is optimized for:

- retrieval
- project memory
- conceptual boundaries
- historical continuity

The code tree is optimized for:

- ownership
- implementation lifecycle
- active vs unsupported surfaces
- future refactoring flexibility

This is why `ALS` and `RES` remain explicit documentation domains even though they do not map neatly to single code packages.

## Historical Layering Context

The old `OBS/NAV/EXE/AUT` decomposition still names useful concerns:

- observation
- navigation
- execution
- automation

Those concerns are no longer the primary docs taxonomy. They survive as historical vocabulary and as sub-concerns inside runtime design.

## Current Organizing Principles

- docs are optimized for agent retrieval and project continuity
- ALAS and research remain first-class documentation domains
- VLM is treated as first-class capability knowledge, not a side detail
- prework and runtime are deliberately separated
- runtime claims must be earned by code, not inferred from plans
