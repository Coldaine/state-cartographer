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
- `scripts/`
  - current active script surface
- `runtime/`
  - first-pass stream-first runtime scaffold for MEmu automation
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
  - repo-wide execution tracker for active tasks, blockers, and immediate next actions
- `docs/AGENTS.md`
  - local index for the docs tree
- `docs/ALS-reference/`
  - ALAS reference-system knowledge
- `docs/RES-research/`
  - research notes, synthesis, and experiments
- `docs/architecture-overview.md`
  - architecture and organizing logic
- `docs/project/`
  - current reality, north star, repo indexing
  - includes `documentation-playbook.md` for docs workflow rules
- `docs/memory/`
  - dated lessons learned and preserved findings
- `docs/workflows/`
  - workflow/task inventory
- `docs/agentPrompts/`
  - code-linked rationale docs for prompt-bearing LLM code
- `docs/prework/`
  - corpus/data preparation procedures
- `docs/runtime/`
  - runtime boundaries, retained runtime design knowledge, draft event schema, and prototype runtime status
  - includes `tiered-automation-stack.md` for current scaffold truth, not canonical architecture
- `docs/dev/`
  - developer workflow docs (testing strategy, etc.)
- `docs/vlm/`
  - VLM profiles, contracts, and prompt guidance
- `docs/plans/`
  - tactical planning docs, including the canonical multi-tier runtime plan and the MEmu transport companion
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
- `scripts/tiered_automation.py`
  - Phase-1 runtime scaffold with Tier-2-first resolution, ADB observe-act support, and an optional prototype template cache
- `runtime/`
  - first-pass stream-first runtime package
  - `transport/`: ADB client, scrcpy substrate wrapper, frame validation, MEmu instance wiring
  - `observation/`: frame health, compact context, frame sampling types
  - `actor/`: prompt builder, schema validation, local actor router, post-action verifier, candidate ranking
  - `controller/`: objective loop, retry policy, transition tracking, action execution, failure codes
  - `replay/`: interface plus no-op implementation
  - `teacher/`: interface plus no-op implementation
  - `logging/`: artifact/event persistence

## Data Surface

- `data/`
  - corpus, labels, screenshots, logs, backups, and other working artifacts
  - preserve by default unless there is a strong reason not to

## Reference Code Surface

- `vendor/AzurLaneAutoScript/`
  - ALAS reference implementation and source of operational prior art

## Validation Surface

- `tests/runtime/`
  - first-pass pure-logic tests for frame health, actor schema, transition tracking, retry policy, and replay noop behavior
- validation is now:
  - runtime syntax checks
  - unit tests for stable runtime helpers
  - script execution
  - documentation consistency checks

## Practical Rule

If you need short orientation, use root `AGENTS.md`.
If you need the exhaustive high-level map, use this file.
If you need the rules for adding or updating docs, use `docs/project/documentation-playbook.md`.
