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
| `data/` | Screenshots, logs, labels, corpora, per-run manifests/events/artifacts |
| `docs/` | Project knowledge layer |
| `scripts/` | Active script surface |
| `state_cartographer/` | Python package: transport layer and future runtime |
| `tests/` | Automated tests |
| `vendor/` | ALAS launch helper and reference snapshots for the external install |

## Docs Map

| Path | Purpose |
|---|---|
| `docs/todo.md` | Current truth, active tasks, blockers |
| `docs/AGENTS.md` | Navigation index for docs/ |
| `docs/north-star.md` | Desired end state |
| `docs/architecture-overview.md` | Organizing logic |
| `docs/repo-index.md` | This file — exhaustive repo map |
| `docs/decisions.md` | Decision log with rationale |
| `docs/transport-methods.md` | Settled capture/input method decisions |
| `docs/ALS-reference/` | ALAS reference-system knowledge |
| `docs/RES-research/` | Research notes and synthesis |
| `docs/memory/` | Dated lessons learned |
| `docs/workflows/` | Workflow/task inventory |
| `docs/prompts/` | Prompt rationale for LLM code |
| `docs/prework/` | Corpus/data preparation procedures |
| `docs/runtime/` | Backend design constraints |
| `docs/dev/` | Testing plan |
| `docs/sessions/` | Tracked human and promoted run summaries |
| `docs/vlm/` | VLM profiles, contracts, prompt guidance |
| `docs/plans/` | Active planning docs |

## Active Plans

| Plan | What It Decides |
|---|---|
| `plans/multi-tier-runtime-implementation-plan-2026-03-24.md` | Tiered runtime architecture (Tier 2 VLM baseline, Tier 1 cache, Tier 3 teacher) |
| `plans/vlm-corpus-sweep-plan.md` | Multi-pass VLM labeling of screenshot corpus to build the state machine |

## Active Script Surface

| File | Purpose |
|---|---|
| `scripts/corpus_sweep.py` | Multi-pass corpus labeling, log alignment, adjudication, and triple extraction |
| `scripts/dock_census_capture.py` | Live dock census capture against the pinned emulator/device |
| `scripts/census_extract.py` | Extract structured census records from captured dock runs |
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
| `config.py` | Transport configuration loading |
| `models.py` | Data models for reports and status |
| `health.py` | Readiness checks and recovery |
| `pilot.py` | Unified facade (recommended entry point) |

## Run Recording

`state_cartographer/run_recording.py` — unified run provenance for production-ish CLIs.

Canonical local run layout:

- `data/runs/<run_id>/manifest.json`
- `data/runs/<run_id>/events.ndjson`
- `data/runs/<run_id>/<lane>/...`
- `data/logs/<date>_<run_id>.log`
- `docs/sessions/auto/<date>_<lane>_<run_id>.md`

## Data Surface

`data/` holds truth artifacts, corpora, screenshots, run manifests, and logs. Canonical runtime provenance lives under `data/runs/`; bulky raw outputs remain gitignored by default.

## Reference Code Surface

ALAS itself lives outside this repo at `D:\_projects\ALAS_original`. Inside this repo, `vendor/launch_alas.ps1` is the launch helper and `vendor/alas_requirements_clean.txt` is the pinned dependency snapshot used to rebuild the external ALAS venv.

## Test Surface

`tests/` — offline/unit tests by default plus opt-in live smoke tests (`pytest -m live`).

## Practical Rule

Short orientation → root `AGENTS.md`.
Exhaustive map → this file.
