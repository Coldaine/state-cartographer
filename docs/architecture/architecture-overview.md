# Architecture Overview

> Historical note: this document was previously `docs/architecture.md` and described `OBS/NAV/EXE/AUT` as primary domains. That decomposition is retained only as historical context.

## Purpose

This document explains how the repo is organized as knowledge, not just as code.

The key distinction is:

- `docs/` organizes **agent knowledge**
- code and data organize **implementation work**

Those are not the same axis, and they should not be forced into one tree.

## Retained Domains

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
| `project/` | repo status, north star, testing posture |
| `architecture/` | organizing principles and architectural map |
| `workflows/` | assignment and workflow knowledge |
| `prework/` | corpus alignment, cleanup, extraction, and data-gathering programs |
| `runtime/` | live-system contracts and retained runtime design constraints |
| `vlm/` | multimodal model profiles, task contracts, prompt policy |
| `plans/` | active and historical planning documents |
| `decisions/` | ADRs and stable project decisions |

## Code and Data Buckets

The implementation side of the repo should be thought about separately from docs:

- `data/` holds truth artifacts and corpora
- `vendor/` holds external code and reference systems
- `prework/` code will hold corpus/data-building logic when that code is re-homed out of `scripts/`
- `vlm/` code should hold model-facing infrastructure and contracts
- `runtime/` code should hold only live-system logic that has actually been earned
- `quarantine/` holds retained but unsupported code

## Historical Layering Context

The old `OBS/NAV/EXE/AUT` decomposition still captures useful concerns:

- observation
- navigation
- execution
- automation

But those are no longer used as the primary documentation taxonomy. They remain useful as historical vocabulary and as sub-concerns inside runtime design, not as top-level doc domains.

## Current Organizing Principles

- Docs are optimized for agent retrieval and project continuity.
- ALAS and research remain first-class knowledge domains.
- VLM is treated as first-class capability knowledge, not as a side detail under a generic observation bucket.
- Prework and runtime are deliberately separated.
- Runtime claims must be earned by code, not inferred from plans.
