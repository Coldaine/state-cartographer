# Repo Index

This document is the exhaustive high-level map of the repository.

Use root `AGENTS.md` for fast orientation.
Use this file when you need the fuller answer to `where does this live?`.

See also:
- [docs/AGENTS.md](/mnt/d/_projects/MasterStateMachine/docs/AGENTS.md)
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
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
- `quarantine/`
  - retained but unsupported material
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

- `docs/AGENTS.md`
  - local index for the docs tree
- `docs/ALS-reference/`
  - ALAS reference-system knowledge
- `docs/RES-research/`
  - research notes, synthesis, and experiments
- `docs/architecture-overview.md`
  - architecture and organizing logic
- `docs/project/`
  - current reality, north star, repo indexing, validation posture
- `docs/workflows/`
  - workflow/task inventory
- `docs/prework/`
  - corpus/data preparation procedures
- `docs/runtime/`
  - runtime boundaries and retained runtime design knowledge
- `docs/vlm/`
  - VLM profiles, contracts, and prompt guidance
- `docs/plans/`
  - tactical and strategic planning docs
- `docs/decisions/`
  - ADR-style decision records
- `docs/vendor-patches/`
  - existing patch/reference bucket retained as-is

## Active Code Surface

- `scripts/corpus_cleanup.py`
  - corpus hygiene: duplicate clustering and black-frame cleanup
- `scripts/kimi_review.py`
  - cheap Kimi-backed visible-first screenshot review
- `scripts/vlm_detector.py`
  - VLM-backed offline detection and labeling tool

## Data Surface

- `data/`
  - corpus, labels, screenshots, logs, backups, and other working artifacts
  - preserve by default unless there is a strong reason not to

## Reference Code Surface

- `vendor/AzurLaneAutoScript/`
  - ALAS reference implementation and source of operational prior art

## Quarantine Surface

- `quarantine/`
  - unsupported retained material from earlier directions
  - treat contents as reference only unless explicitly re-earned

## Validation Surface

- there are currently no committed automated checks in the repo
- validation is presently script execution, corpus inspection, and documentation consistency checks

## Practical Rule

If you need short orientation, use root `AGENTS.md`.
If you need the exhaustive high-level map, use this file.
