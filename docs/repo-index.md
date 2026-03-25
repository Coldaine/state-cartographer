# Repo Index

This document is the exhaustive high-level map of the repository.

Use root `AGENTS.md` for fast orientation.
Use this file when you need the fuller answer to `where does this live?`.

See also:
- [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md)
- [todo.md](/mnt/d/_projects/MasterStateMachine/docs/todo.md)
- [architecture-overview.md](/mnt/d/_projects/MasterStateMachine/docs/architecture-overview.md)

## Root-Level Map

- `AGENTS.md`
  - mandatory repo entrypoint
- `CLAUDE.md`
  - pointer file that defers to `AGENTS.md`
- `pyproject.toml`
  - Python project configuration and tool configuration
- `uv.lock`
  - locked dependency state
- `configs/`
  - project configuration artifacts
- `data/`
  - screenshots, logs, labels, corpora, backups, and other working artifacts
- `docs/`
  - project knowledge layer
- `examples/`
  - example/reference artifacts
- `hooks/`
  - hook-related code and assets retained in the repo
- `scripts/`
  - current active script surface
- `vendor/`
  - external reference code, including ALAS

## Root-Level Support And Generated Paths

These exist in the worktree but are not primary project knowledge or product surfaces.

- `.git/`
- `.github/`
- `.githooks/`
- `.omc/`
- `.ruff_cache/`
- `.venv/`
- `state_cartographer.egg-info/`
- `.codexignore`
- `.gitattributes`
- `.gitignore`
- `.gitmodules`

## Docs Map

- `docs/todo.md`
  - repo-wide tracker for current truth, active tasks, blockers, and immediate next actions
- `docs/AGENTS.md`
  - local index for the docs tree
- `docs/ALS-reference/`
  - ALAS reference-system knowledge
- `docs/RES-research/`
  - research notes, synthesis, and experiments
- `docs/architecture-overview.md`
  - architecture and organizing logic
- `docs/north-star.md`
  - desired end state
- `docs/repo-index.md`
  - exhaustive high-level repo map
- `docs/documentation-playbook.md`
  - docs workflow rules
- `docs/memory/`
  - dated lessons learned and preserved findings
  - includes `2026-03-25-memu-transport-probe-results.md` for the first live MEmu transport verdict
- `docs/workflows/`
  - workflow/task inventory
- `docs/agentPrompts/`
  - code-linked rationale docs for prompt-bearing LLM code
- `docs/prework/`
  - corpus/data preparation procedures
- `docs/runtime/`
  - runtime boundaries, retained runtime design knowledge, external tool requirements, and borrowed-tool intake/setup notes
  - includes `agent-control-tool-requirements.md` for borrowed substrate selection criteria
  - includes `health-heartbeat-logging.md` for readiness tiers, layered heartbeat design, structured event logging, and evidence layout
  - includes `borrowed-control-tool-setup.md` for local setup and compatibility-spike procedure
- `docs/dev/`
  - developer workflow docs (testing strategy, etc.)
  - includes `testingADB.md` for live ADB/emulator integration testing and evidence expectations
- `docs/vlm/`
  - VLM profiles, contracts, and prompt guidance
  - includes `llama-swap-quickstart.md` for local model serving and endpoint usage
- `docs/plans/`
  - tactical planning docs, including the canonical runtime plan and the MEmu transport companion
  - includes `adb-touch-vision-substrate-selection-2026-03-25.md` for the 10-candidate borrowed-substrate evaluation and final touch/vision recommendation
- `docs/vendor-patches/`
  - existing patch/reference bucket retained as-is

## Active Code Surface

- `scripts/corpus_cleanup.py`
  - corpus hygiene: duplicate clustering and black-frame cleanup
- `scripts/kimi_review.py`
  - cheap Kimi-backed visible-first screenshot review
- `scripts/vlm_detector.py`
  - VLM-backed offline detection and labeling tool
- `scripts/memu_transport.py`
  - CLI for MEmu transport probes: bootstrap, doctor, connect, capture, input, probe

## Transport Package

- `state_cartographer/transport/`
  - borrowed-substrate surface for emulator control
  - `config.py` — transport config from `configs/memu.json`
  - `models.py` — probe verdicts, reports, and manifest data models
  - `artifacts.py` — timestamped artifact directory management
  - `discovery.py` — tool bootstrap (adb, maamcp, scrcpy, adbfriend)
  - `adb.py` — thin ADB subprocess wrapper
  - `maamcp.py` — MaaAdapter (maafw with adb fallback), MaaMCP probe
  - `scrcpy_probe.py` — scrcpy coexistence testing and verdict
  - `health.py` — doctor readiness check, recovery ladder

## Data Surface

- `data/`
  - corpus, labels, screenshots, logs, backups, and other working artifacts
  - preserve by default unless there is a strong reason not to
  - `data/events/memu-transport/` holds transport bootstrap/probe artifacts and dated session reports

## Reference Code Surface

- `vendor/AzurLaneAutoScript/`
  - ALAS reference implementation and source of operational prior art

## Validation Surface

- `tests/transport/test_transport.py`
  - 15 pure-code tests for transport config, models, discovery, and health logic
  - 3 live transport smoke tests for doctor, control-adapter capture/input, and recovery
- validation is presently test execution, script execution, corpus inspection, and documentation consistency checks

## Practical Rule

If you need short orientation, use root `AGENTS.md`.
If you need the exhaustive high-level map, use this file.
If you need the rules for adding or updating docs, use `docs/documentation-playbook.md`.
