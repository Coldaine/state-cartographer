# ALAS Build Plan

> Historical note: this document was extracted from the research-oriented `docs/RES-research/RES-alas-build-plan.md` during the 2026 documentation realignment.

## Purpose

This is the operational prework program for turning ALAS into repo-owned artifacts and inventories.

## Outputs

The prework should produce:

1. assignment inventory
2. action inventory
3. event/recording inventory
4. mapping from assignments to required screens, states, and actions
5. artifacts that future runtime work can consume without wrapping ALAS as the operator

## Core Workstreams

### Assignment inventory

Enumerate assignable ALAS commands/tasks and record:

- command name
- category
- defining module
- scheduler presence

### Action inventory

Separate:

- primitive emulator actions
- semantic UI actions
- likely instrumentation points

### Recording layer

Define what needs to be recorded during ALAS runs so the corpus is useful for later analysis.

Minimum retained questions:

- what assignment was active?
- what action was attempted?
- what screen was seen before and after?
- what evidence exists that the action worked or failed?

### Assignment-to-artifact mapping

Connect assignment semantics to:

- relevant screens and substates
- required entry conditions
- known recovery conditions
- completion evidence

## Relationship To Research

The reasoning and justification for this work remain in [RES-alas-build-plan.md](../RES-research/RES-alas-build-plan.md). This doc keeps only the operational prework side.
