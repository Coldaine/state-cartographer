# ALAS State-Machine Build Plan

> Historical note: moved from `docs/research/RES-alas-build-plan.md` during the 2026 documentation realignment.

This document remains in `RES` because it captures the reasoning for using ALAS as a build source and translation target.

For the operational extraction program, see [ALAS Build Plan](../prework/alas-build-plan.md).

## Problem Statement

The repo currently has a page graph:

- states
- transitions
- deterministic transition actions such as `adb_tap`

That is necessary, but incomplete.

ALAS also has:

- assignable scheduler commands/tasks
- a real emulator action surface
- recovery logic
- live execution loops
- task-specific navigation and handling logic

If we stop at `graph.json`, we only model the page-navigation layer. We do not yet model what the automation can be assigned to do, how those assignments map onto graph regions, or how real emulator actions are executed and recorded.

## Current Gap

What exists:

- graph schema for states and transitions
- ALAS-derived Azur Lane graph
- session state tracking
- ADB bridge
- observation and locate tools

What is missing:

- canonical inventory of assignable ALAS commands/tasks
- canonical inventory of ALAS emulator actions
- event log of actual executed actions
- mapping from assignment -> required states -> transition plan -> completion
- runtime takeover loop that can run assignments end to end

## Research Objective

Preserve the conceptual translation from ALAS into repo-owned artifacts:

1. assignment inventory
2. action inventory
3. state graph
4. execution event log
5. assignment runner / takeover runtime

The operationalized version of this program now lives in [ALAS Build Plan](../prework/alas-build-plan.md).
