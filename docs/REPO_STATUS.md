# REPO_STATUS.md

## Repo State

This repo has been deliberately stripped back to a minimal, trusted, data-first core.

The previous shape implied a runtime, scheduler, graph-navigation layer, and executor surface that the code had not earned. Those claims have been removed from active code.

## Labels

### `active`

Trusted code used right now:

- `scripts/label_raw_stream.py`
- `scripts/screenshot_dedupe.py`
- `scripts/delete_black_frames.py`
- `scripts/vlm_detector.py`

### `quarantine`

Retained but not trusted or supported:

- `quarantine/scripts/pilot_bridge.py`

### `data`

Preserved source-of-truth assets:

- `data/**`
- existing prompt outputs and labeling artifacts
- ALAS logs and screenshot corpora

### `vendor`

External reference code:

- `vendor/AzurLaneAutoScript/`

## What Was Removed

Removed from active code:

- executor and scheduler scaffolding
- resource and task-model scaffolding
- graph/navigation scaffolding
- anchor calibration and mock runtime side paths
- analysis utilities not required by the ALAS log plus screenshot corpus workflow

## What Was Preserved As Documentation

Some semantics remain valuable even though the code was removed:

- historical event schema material under [ALS-event-schema.md](/mnt/d/_projects/MasterStateMachine/docs/alas/ALS-event-schema.md)
- workflow inventory under [docs/execution/EXE-workflows.md](/mnt/d/_projects/MasterStateMachine/docs/execution/EXE-workflows.md)
- ALAS-related research and synthesis docs

These are references, not active contracts.

## Current Supported Workflow

The active workflow is:

1. collect ALAS logs and screenshots
2. align screenshots to log events
3. clean and dedupe corpus artifacts
4. run offline VLM-based labeling or adjudication
5. use the rebuild interview to define what comes next
