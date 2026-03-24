# Branch Repair And Clean PR Plan

## Purpose

This document captures the current branch-history problem and the exact repair plan.

It is intentionally narrow:
- what went wrong with the current branch base
- what work must be preserved
- how to rebuild a clean PR from `origin/main` without losing work

## Current Situation

Observed facts:

- current working branch: `codex/carry-forward-20260324`
- current branch head: `722c73c`
- `origin/main` head: `a8f24e5`
- merge base between `origin/main` and `HEAD`: `25acef3`

This means the current branch is not based on current `origin/main`.

The branch was carried forward from the older snapshot line instead of being recreated from current `main`.

## Commits We Intend To Preserve

These are the commits currently on the branch beyond the merge base:

1. `f907d79` `Remove tests and sync repo docs`
2. `bd69cea` `Purge remaining test artifacts`
3. `c4ae032` `Reset corpus review surface`
4. `722c73c` `Record corpus review lessons`

These commits already exist on the remote branch. The work is not lost.

## Submodule Pointer Change

The branch also carries a submodule pointer change for:

- [vendor/AzurLaneAutoScript](/mnt/d/_projects/MasterStateMachine/vendor/AzurLaneAutoScript)

Observed diff against `origin/main`:

- old pointer: `adfe978`
- current pointer on this branch: `3bd8a21`
- summarized submodule log: `Bug fix (#5567)`

Important fact:

- this pointer change first appears in `f907d79`

So if `f907d79` is cherry-picked as-is, the submodule bump comes with it unless deliberately edited out.

## What Went Wrong

The failure was not loss of work.

The failure was branch hygiene:

- work was continued on top of an older non-main base
- the branch was then treated like a clean PR branch
- the resulting PR mixes valid work with an avoidable ancestry mess

## Repair Goal

Create a new branch from current `origin/main` that contains only the intended work, in a clean linear history.

## Repair Plan

1. Keep the current branch untouched as the safety anchor.
   - do not rewrite or discard `codex/carry-forward-20260324`

2. Create a fresh branch from `origin/main`.
   - example: `codex/clean-corpus-review-reset`

3. Cherry-pick the intended commits onto the fresh branch in order:
   - `f907d79`
   - `bd69cea`
   - `c4ae032`
   - `722c73c`

4. Decide intentionally whether to keep the ALAS submodule pointer bump.
   - if wanted, keep it
   - if not wanted, reset the submodule pointer on the clean branch before final commit

5. Validate the rebuilt branch.
   - compare `git diff --name-status origin/main...HEAD`
   - confirm only intended files changed
   - confirm the branch is now directly based on current `origin/main`
   - rerun the lightweight script validation:
     - `uv run python -m py_compile scripts/corpus_cleanup.py scripts/kimi_review.py scripts/vlm_detector.py`

6. Push the clean branch.

7. Open a replacement PR against `main`.

8. Only after the replacement PR looks correct:
   - close or abandon PR `#18`

## Preferred Default

Unless there is a reason to preserve the ALAS bump, the safer default is:

- rebuild from `origin/main`
- cherry-pick the four commits
- drop the submodule pointer change if it is not part of the intended corpus-review reset

That produces the narrowest clean PR.

## Why This Is Safe

- the current branch remains intact
- the four source commits already exist on the remote
- cherry-picking copies work; it does not destroy the original commits
- if a cherry-pick conflicts, the source branch still exists unchanged

## Success Criteria

This repair is successful when:

- the new branch is based on current `origin/main`
- the intended commits are preserved
- the submodule pointer is included only if explicitly intended
- the replacement PR has clean ancestry and expected diff scope
