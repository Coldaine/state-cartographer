# Repo Index

Exhaustive high-level map of the repository.

Use root `AGENTS.md` for fast orientation. Use this file for the full answer to "where does this live?"

## Root-Level Map

| Path | Purpose |
|---|---|
| `AGENTS.md` | Mandatory repo entrypoint |
| `CLAUDE.md` | Pointer to AGENTS.md |
| `pyproject.toml` | Python project config |
| `configs/` | Project configuration (emulator serial, tool posture) |
| `data/` | Screenshots, logs, labels, corpora, working artifacts |
| `docs/` | Project knowledge layer |
| `scripts/` | Active script surface |
| `state_cartographer/` | Python package: transport layer and future runtime |
| `tests/` | Automated tests |
| `vendor/` | External reference code (ALAS) |

## Docs Map

| Path | Purpose |
|---|---|
| `docs/todo.md` | Current truth, active tasks, blockers |
| `docs/AGENTS.md` | Navigation index for docs/ |
| `docs/north-star.md` | Desired end state |
| `docs/architecture-overview.md` | Organizing logic |
| `docs/repo-index.md` | This file — exhaustive repo map |
| `docs/documentation-playbook.md` | Doc workflow rules |
| `docs/decisions.md` | Decision log with rationale |
| `docs/ALS-reference/` | ALAS reference-system knowledge |
| `docs/RES-research/` | Research notes and synthesis |
| `docs/memory/` | Dated lessons learned |
| `docs/workflows/` | Workflow/task inventory |
| `docs/agentPrompts/` | Prompt rationale for LLM code |
| `docs/prework/` | Corpus/data preparation procedures |
| `docs/runtime/` | Runtime contracts, backend lessons, health design, tool requirements, emulator reference |
| `docs/dev/` | Developer workflow docs (testing) |
| `docs/vlm/` | VLM profiles, contracts, prompt guidance |
| `docs/plans/` | Active planning docs |

## Active Plans

| Plan | What It Decides |
|---|---|
| `plans/multi-tier-runtime-implementation-plan-2026-03-24.md` | Tiered runtime architecture (Tier 2 VLM baseline, Tier 1 cache, Tier 3 teacher) |

## Active Script Surface

| File | Purpose |
|---|---|
| `scripts/corpus_cleanup.py` | Corpus hygiene: duplicate clustering, black-frame cleanup |
| `scripts/kimi_review.py` | Cheap Kimi-backed screenshot review |
| `scripts/vlm_detector.py` | VLM-backed offline detection and labeling |
| `scripts/stress_test_adb.py` | ADB screencap stress test and validation |

## Transport Package

`state_cartographer/transport/` — adbutils + MaaTouch implementation:

| File | Purpose |
|---|---|
| `__init__.py` | Transport package exports |
| `adb.py` | adbutils-based ADB client (no subprocess) |
| `maatouch.py` | MaaTouch precision touch protocol |
| `capture.py` | Screenshot capture methods |
| `config.py` | Transport configuration loading |
| `models.py` | Data models for reports and status |
| `health.py` | Readiness checks and recovery |
| `artifacts.py` | Event persistence |
| `pilot.py` | Unified facade (recommended entry point) |

## Data Surface

`data/` holds truth artifacts, corpora, screenshots, logs. Most subdirectories are gitignored (events, stress_test, raw_stream). Preserve committed files by default.

## Reference Code Surface

`vendor/AzurLaneAutoScript/` — ALAS reference implementation. Source of operational prior art, adbutils patterns, MaaTouch binary, and screenshot method examples.

## Test Surface

`tests/` — transport tests (unit + live smoke tests).

## Practical Rule

Short orientation → root `AGENTS.md`.
Exhaustive map → this file.
Doc workflow rules → `docs/documentation-playbook.md`.
