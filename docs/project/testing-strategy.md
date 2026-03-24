# Testing Strategy

> Historical note: this document was previously `docs/testing-strategy.md`.

## Purpose

Testing should follow the current bucket structure rather than the retired layered-domain structure.

## Current Test Priorities

### Prework tests

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

### Runtime tests

Only after runtime code is re-earned:

- backend smoke checks
- observation contract checks
- workflow-level integration tests

### Documentation checks

Whenever docs move or merge:

- path existence
- internal link validity
- legacy-path cleanup
- consistency between `AGENTS.md`, `CLAUDE.md`, and the docs tree

## Current Reality

The surviving automated coverage is still centered on the current script surface. As code is moved into `prework/` and `vlm/`, the tests should follow those buckets rather than remain attached to standalone scripts.
