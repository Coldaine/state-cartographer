# ALAS Build Plan

> Historical note: this document was extracted from the research-oriented `docs/RES-research/RES-alas-build-plan.md` during the 2026 documentation realignment.

## Purpose

This is the operational prework program for turning ALAS into repo-owned artifacts and inventories.

It is about extracting durable knowledge and datasets from ALAS. It is not a claim that ALAS should remain the operator.

See also:
- [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)

## Why ALAS Is Still Used Here

ALAS matters in prework because it provides more than a page graph.

It also provides:
- assignable task and command structure
- real emulator action patterns
- recovery behavior
- logs and screenshots from actual runs
- operational evidence about what a future runtime must eventually replace

If the repo only preserves page/navigation artifacts, it loses a large part of the useful prior art.

## Outputs

The prework should produce:

1. assignment inventory
2. action inventory
3. event/recording inventory
4. mapping from assignments to required screens, states, and actions
5. durable corpus artifacts for later labeling and analysis
6. optional read-heavy collection artifacts such as ship census or roster snapshots

## Core Workstreams

### 1. Assignment inventory

Enumerate assignable ALAS commands/tasks and record:
- command name
- category
- defining module
- scheduler presence
- obvious entry and completion evidence

### 2. Action inventory

Separate:
- primitive emulator actions
- semantic UI actions
- likely instrumentation points
- actions that still appear worth preserving after the script peel-back

### 3. Recording layer

Define what needs to be recorded during ALAS runs so the corpus is useful for later analysis.

Minimum retained questions:
- what assignment was active?
- what action was attempted?
- what screen was seen before and after?
- what evidence exists that the action worked or failed?

### 4. Assignment-to-artifact mapping

Connect assignment semantics to:
- relevant screens and substates
- required entry conditions
- known recovery conditions
- completion evidence

### 5. Data collection programs

Some prework is read-heavy rather than action-heavy. Treat these as offline collection programs, not as proof of a runtime scheduler.

Examples:
- ship census / dock paging
- ship detail extraction
- formation audit
- resource scan
- dorm status collection

For these programs, the durable value is:
- the collection target
- the required screens and pagination logic
- the output schema
- the evidence needed to resume or verify progress

Do not assume a dedicated `data_collector.py` or second scheduler already exists.

## Durable Findings From Earlier ALAS Work

These findings should be preserved even as older scripts and plans are removed:
- the ALAS harness produced real logs and screenshots
- historical graph/anchor tooling was not sufficient to classify recent live ALAS screenshots reliably
- provider and screenshot-path behavior materially affected whether runs looked stable or inert
- ALAS-derived navigation coordinates matched some controls closely and diverged noticeably on others
- read-heavy collection workflows are materially different from short action workflows and should be documented separately

## Practical Rule

Use this document as the executable ALAS-derived artifact program.

Do not treat it as evidence that the old repo-side ALAS helper scripts still exist.
