# Testing Strategy

> Historical note: this document was previously `docs/testing-strategy.md`.

## Purpose

This document defines testing policy for the current repo shape.

It separates present validation expectations from future runtime testing that has not been re-earned yet.

See also:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)

## Current Validation Policy

There is currently no committed automated test suite in the repo.

Validation should stay focused on the active surface:

- corpus pipeline spot checks and script-level verification
- ALAS log to screenshot alignment
- screenshot deduplication
- black-frame cleanup
- corpus manifest integrity where applicable
- VLM offline labeling/adjudication behavior
- model profile selection
- task contract validation
- structured output handling
- local vs remote adjudication behavior
- documentation consistency checks when docs move or merge
- path existence
- internal link validity
- legacy-path cleanup
- consistency between `AGENTS.md`, `CLAUDE.md`, and the docs tree

## Current Boundary

The active validation surface is still centered on the retained scripts and docs. If automated checks return later, they should follow the active `prework/` and `vlm/` code buckets rather than historical standalone script names.

## Future Runtime Testing

These tests are not current expectations. They become relevant only after live runtime code is re-earned.

- backend smoke checks
- observation contract checks
- workflow-level integration tests
- operator-path validation
