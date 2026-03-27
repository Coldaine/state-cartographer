# Architecture Overview

## Purpose

How the repo is organized as knowledge and code.

## Two Axes

- `docs/` organizes project knowledge (for retrieval, project memory, and continuity)
- Code and data organize implementation work (for ownership, lifecycle, and active surfaces)

These are different axes and should not be forced into one tree.

## Documentation Domains

Two explicit documentation domains:
- `ALS-reference/` — ALAS as reference system, corpus source, and comparison point
- `RES-research/` — research, experiments, hypotheses, and synthesis

Everything else in `docs/` is a knowledge bucket.

## Knowledge Buckets

| Bucket | Purpose |
|---|---|
| root `docs/*.md` | current truth, north star, repo index, doc rules |
| `memory/` | dated lessons learned and findings worth preserving |
| `workflows/` | workflow and task knowledge |
| `prework/` | corpus alignment, cleanup, data-gathering procedures |
| `runtime/` | live-system contracts, backend lessons, health design |
| `vlm/` | multimodal model profiles, task contracts, prompt policy |
| `plans/` | tactical and strategic planning documents |
| `agentPrompts/` | code-linked prompt rationale for prompt-bearing LLM code |
| `dev/` | developer workflow docs (testing, ADB integration) |

## Code and Data Buckets

| Path | Purpose |
|---|---|
| `state_cartographer/` | Python package: transport layer and future runtime code |
| `scripts/` | Active script-shaped tooling (corpus cleanup, kimi review, vlm detector) |
| `data/` | Truth artifacts, corpora, screenshots, logs |
| `vendor/` | External reference code (ALAS, scrcpy) |
| `configs/` | Project configuration (emulator serial, tool posture) |
| `tests/` | Automated tests |
| `examples/` | Reference/example artifacts |

## Current Implementation State

- `state_cartographer/transport/` is implemented — adb, maatouch, health, models, pilot facade
- Active scripts: `corpus_cleanup.py`, `kimi_review.py`, `vlm_detector.py`, `stress_test_adb.py`
- No live runtime exists yet (transport layer done; VLM corpus sweep is next)
- Substrate decision made: adbutils + MaaTouch (see [decisions.md](decisions.md))

## Organizing Principles

- Docs are optimized for agent retrieval and project continuity
- ALAS and research remain first-class documentation domains
- VLM is first-class capability knowledge
- Prework and runtime are deliberately separated
- Runtime claims must be earned by code, not inferred from plans
- One authoritative doc per question — no duplication
