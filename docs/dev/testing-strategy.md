# Testing Strategy

## Core Policy

- No mocks.
- No tests for files until they are mostly complete and doing real work.
- Tests should validate real behavior, not ceremony around incomplete code.

## Current State

There are no committed automated checks in the repo. The active code surface is three scripts under `scripts/`. Validation right now is script execution, corpus inspection, and documentation consistency.

## When Tests Get Written

Tests become relevant when a file is stable enough that:

- it has a clear input/output contract
- it is being used in a real workflow
- breaking it would cost real time to diagnose

Until then, the file is still being shaped and tests would just slow that down.

## What Tests Should Look Like

When tests do exist:

- they hit real code paths, not mocked interfaces
- they use real data artifacts where practical
- they verify observable outcomes, not implementation details

## Future Runtime Testing

These become relevant only after live runtime code is re-earned:

- backend smoke checks
- observation contract checks
- workflow-level integration tests
- operator-path validation
