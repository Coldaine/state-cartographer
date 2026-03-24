# Testing Strategy

> Historical note: this document was previously `docs/testing-strategy.md`.

## Purpose

This document defines testing policy for the current repo shape.

It separates current testing expectations from future runtime testing that has not been re-earned yet.

See also:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)

## Current Testing Policy

Current automated testing should stay focused on the active surface.

### Prework and corpus tests

Validate the corpus pipeline:

- ALAS log to screenshot alignment
- screenshot deduplication
- black-frame cleanup
- corpus manifest integrity

### VLM contract tests

Validate the multimodal interface layer:

- model profile selection
- task contract validation
- structured output handling
- local vs remote adjudication behavior

### Documentation checks

Whenever docs move or merge:

- path existence
- internal link validity
- legacy-path cleanup
- consistency between `AGENTS.md`, `CLAUDE.md`, and the docs tree

## Current Test Boundary

The surviving automated coverage is still centered on the current script surface. As code is re-homed into `prework/` and `vlm/`, the tests should follow those buckets rather than remain attached to standalone scripts.

## Future Runtime Testing

These tests are not current expectations. They become relevant only after live runtime code is re-earned.

- backend smoke checks
- observation contract checks
- workflow-level integration tests
- operator-path validation
