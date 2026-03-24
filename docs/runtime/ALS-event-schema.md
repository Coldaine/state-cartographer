# Event Schema — Draft Inspiration

> **Status: Draft / inspiration only.** No code emits this. The final recording format will be shaped by what the runtime actually needs, not by this sketch. Treat it as one possible starting point, not a commitment.

This document sketches a possible NDJSON event format for recording what happens during automation runs — taps, screenshots, recoveries, assignment lifecycle, etc.

It was originally derived from thinking about how to bridge ALAS concepts into a future runtime recording layer. The actual schema should be designed when the runtime exists and the real requirements are known.

See also:
- [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md)
- [ALS-live-ops.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-live-ops.md)

## Design Rules

- append-only event stream
- one event per meaningful execution step
- record both `semantic_action` and `primitive_action` when both are known
- record enough context to replay or analyze failures later
- prefer NDJSON / JSONL for easy streaming and incremental writes

## Event Types

### 1. Assignment Lifecycle

Marks assignment-level boundaries.

Examples:

- assignment start
- assignment success
- assignment failure
- assignment escalated

### 2. Observation

Records sensing steps.

Examples:

- screenshot captured
- hierarchy dumped
- foreground package checked
- state confirmed
- ambiguity detected

### 3. Execution

Records actual emulator actions.

Examples:

- tap
- swipe
- drag
- app start
- app stop
- goto main
- popup confirm

### 4. Recovery

Records recovery decisions and fallback actions.

Examples:

- page unknown
- retry transition
- restart app
- fallback to main
- escalate to human

## Base Event Shape

```json
{
  "ts": "2026-03-14T21:15:01.123Z",
  "run_id": "run-20260314-001",
  "session_id": "session-001",
  "serial": "127.0.0.1:21513",
  "assignment": "Commission",
  "event_type": "execution",
  "semantic_action": "handle_popup_confirm",
  "primitive_action": "click",
  "target": "POPUP_CONFIRM",
  "coords": [1120, 640],
  "gesture": null,
  "package": "com.YoStarEN.AzurLane",
  "state_before": "page_commission_popup",
  "state_after": "page_commission",
  "screen_before": "runs/run-20260314-001/screens/00041-before.png",
  "screen_after": "runs/run-20260314-001/screens/00042-after.png",
  "ok": true,
  "duration_ms": 427,
  "error": null
}
```

## Required Fields

- `ts`
- `run_id`
- `serial`
- `event_type`
- `ok`

## Strongly Recommended Fields

- `session_id`
- `assignment`
- `semantic_action`
- `primitive_action`
- `target`
- `package`
- `state_before`
- `state_after`
- `screen_before`
- `screen_after`
- `duration_ms`
- `error`

## Field Definitions

### Identification

- `ts`: ISO 8601 UTC timestamp
- `run_id`: unique run identifier
- `session_id`: logical navigation/execution session id
- `serial`: emulator/device serial

### Assignment Context

- `assignment`: scheduler command or repo-owned assignment id
- `assignment_attempt`: optional monotonic retry count for the assignment

### Event Classification

- `event_type`: one of `assignment | observation | execution | recovery`
- `semantic_action`: human-meaningful action name such as `ui_goto_main`
- `primitive_action`: low-level device action such as `click`, `swipe`, `app_start`

### Targeting

- `target`: symbolic target name when available, such as `GOTO_MAIN`
- `coords`: `[x, y]` for taps or `[x1, y1, x2, y2]` for gestures if compact
- `gesture`: structured gesture payload for swipes/drags when needed

### Runtime Context

- `package`: foreground package at action time
- `state_before`: state id before action
- `state_after`: state id after action
- `screen_before`: path to screenshot before action
- `screen_after`: path to screenshot after action
- `hierarchy_before`: optional path to UI hierarchy snapshot
- `hierarchy_after`: optional path to UI hierarchy snapshot

### Outcome

- `ok`: boolean success/failure
- `duration_ms`: action duration
- `error`: error string or exception class
- `notes`: optional extra context

## Event Examples

### Assignment Start

```json
{
  "ts": "2026-03-14T21:15:00.000Z",
  "run_id": "run-20260314-001",
  "serial": "127.0.0.1:21513",
  "assignment": "Commission",
  "event_type": "assignment",
  "semantic_action": "assignment_start",
  "primitive_action": null,
  "ok": true
}
```

### Observation

```json
{
  "ts": "2026-03-14T21:15:00.412Z",
  "run_id": "run-20260314-001",
  "serial": "127.0.0.1:21513",
  "assignment": "Commission",
  "event_type": "observation",
  "semantic_action": "state_confirm",
  "primitive_action": "screenshot",
  "state_after": "page_main",
  "screen_after": "runs/run-20260314-001/screens/00001.png",
  "ok": true
}
```

### Recovery

```json
{
  "ts": "2026-03-14T21:19:44.002Z",
  "run_id": "run-20260314-001",
  "serial": "127.0.0.1:21513",
  "assignment": "Commission",
  "event_type": "recovery",
  "semantic_action": "ui_goto_main",
  "primitive_action": "click",
  "target": "GOTO_MAIN",
  "state_before": "page_unknown",
  "state_after": "page_main",
  "ok": true,
  "duration_ms": 1380
}
```
