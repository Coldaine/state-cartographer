# Current Reality

## Purpose

This document says where the project actually stands right now.

It exists so `AGENTS.md` does not have to carry status narrative.

See also:
- [north-star.md](/mnt/d/_projects/MasterStateMachine/docs/project/north-star.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [repo-index.md](/mnt/d/_projects/MasterStateMachine/docs/project/repo-index.md)

## Current State

As of 2026-03-24:

- the repo has undergone a broad peel-back and documentation realignment
- a large portion of the old runtime/navigation/script surface has been intentionally removed
- the most trustworthy active path remains the ALAS log plus screenshot corpus workflow
- `scripts/vlm_detector.py` is still an offline labeling/adjudication tool, not a re-earned live runtime primitive

## What Is Real Right Now

The currently trusted active script surface is small:

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

These support:

- ALAS log alignment
- corpus hygiene
- offline VLM-assisted labeling and review

## Preserved Findings From Earlier Live Work

The repo should still remember these durable findings from earlier ALAS/live investigation:

- the ALAS harness did produce real runtime artifacts, including logs and screenshots
- historical graph and anchor paths failed to classify recent live ALAS screenshots reliably enough to serve as trusted orientation
- screenshot/provider behavior materially affected whether automation appeared stable or inert
- some ALAS-derived coordinates matched observed controls closely, while others diverged enough to require revalidation against live evidence

## What Is Not Settled

The repo is not yet settled on:

- a re-earned live operator path
- a trusted runtime contract between observation, action, and recovery
- the final code layout for `prework`, `vlm`, and `runtime`
- the final assignment contract that tells the agent what to attempt and how success is judged

## Important Constraint

Historical docs still contain valuable project memory, but some of them describe a broader or more mature runtime than the current code supports.

Treat older runtime claims as design knowledge unless the corresponding code has been explicitly re-earned.
