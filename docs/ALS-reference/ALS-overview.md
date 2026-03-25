# ALS — ALAS Reference System

> Historical note: moved from `docs/alas/ALS-overview.md` during the 2026 documentation realignment.

**Status: Active reference system and corpus source, not the shipped runtime**

ALAS (AzurLaneAutoScript) is a long-lived automation framework for Azur Lane. In this repo it is not the runtime being built. It is a reference implementation, an operational evidence base, and a source of screenshots, logs, patches, and learned failure cases.

See also:
- [ALS-live-ops.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-live-ops.md)
- [ALS-event-schema-sketch.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/ALS-event-schema-sketch.md)
- [alas-artifacts.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-artifacts.md)

## Role in State Cartographer

- **Reference implementation**: ALAS already solved page detection, deterministic navigation, scheduling, and recovery for one concrete game.
- **Corpus source**: ALAS runs can produce screenshots and logs that remain useful for offline analysis and labeling.
- **Operational prior art**: ALAS exposes real workflow complexity, real failure handling, and real naming conventions.
- **Not the live control plane**: this repo should not pretend that using ALAS is equivalent to shipping State Cartographer runtime behavior.

## Why ALAS Matters

ALAS matters because it proves the problem is real and tractable.

It gives the repo:
- mature operational prior art
- real workflow complexity
- real recovery patterns
- a concrete target for comparison
- evidence about what breaks in live automation, not just what looks clean on paper

## Conceptual Mapping

The mapping from ALAS concepts into repo concepts is still useful, but it is conceptual only.

| ALAS Component | Repo Concept |
|---|---|
| `module/ui/page.py` | explicit page/state knowledge |
| `module/ui/assets.py` | anchors, regions, and UI cues |
| `module/ui/ui.py` | locate + goto patterns |
| scheduler commands/tasks | assignment/workflow inventory |
| device control and screenshot layers | operator/runtime backend requirements |

This table is a reasoning aid. It is not a claim that equivalent repo code currently exists or is trustworthy.

## What Exists Today

The durable ALAS surfaces in this repo are:
- `vendor/AzurLaneAutoScript/`
- ALAS logs under `vendor/AzurLaneAutoScript/log/`
- local vendor patches described in `ALS-live-ops.md`
- screenshot/corpus artifacts under `data/` when collection has been run
- ALS reference docs in this folder

Do not assume older repo-side ALAS helper scripts still exist just because older docs or plans mention them. Most of that script surface has been deliberately removed.

## Key Findings Preserved From ALAS Work

- **ALAS labels are task-context labels, not pure visual labels**: a task/page name in ALAS does not necessarily mean the visible frame matches that label in a visually strict sense.
- **Black-frame behavior is operationally important**: black frames often point to screenshot/provider churn or recovery issues rather than simple page-classification failure.
- **Screenshot transport matters**: different screenshot methods materially change whether the system appears stable or inert.
- **Some failures are domain-specific and recurring**: certain Azur Lane flows repeatedly trigger distinct failure classes that are worth remembering as named problems.

## Operational Pointers

- active config is typically under `vendor/AzurLaneAutoScript/config/`
- logs are under `vendor/AzurLaneAutoScript/log/`
- live-run handling rules are in `ALS-live-ops.md`
- any future ALAS-derived event recording should be treated as unsettled until the runtime proves it needs a concrete schema

## How To Use ALAS Correctly

- Use it as reference architecture.
- Use it as a corpus and operational truth source.
- Use it to understand workflow complexity and failure modes.
- Do not treat its internal task/page names as automatically valid visual labels.
- Do not treat wrapping or launching ALAS as equivalent to the runtime this repo intends to build.
