# EXE — Execution

**Status: MVP placeholder prototype (March 2026)**

Execution answers: "how do I perform actions in the game?" Run task action sequences, handle gestures, manage the backend connection, read resources from the screen.

## Build order

Layer 3 — depends on Navigation (tasks navigate to entry states) and Observation (verify arrival, read screen content). Automation depends on this (scheduler triggers execution).

## What it covers

- Task execution engine (executor.py)
- Backend contract (the interface between runtime logic and device control)
- Action types (tap, swipe, wait, navigate, assert_state, read_resource, conditional, repeat)
- Gestures (parameterized swipes, drags, scrolls — first-class actions)
- Task definitions (tasks.json schema and validation)
- Resource reading from game UI (OCR, VLM, pixel regions)
- Event logging (append-only NDJSON record of everything)

## What exists today

- `scripts/executor.py` — task execution with pluggable backends (pilot, adb, mock)
- `scripts/task_model.py` — task definition validation and lifecycle
- `scripts/resource_model.py` — resource store data structure (MVP placeholder)
- `scripts/execution_event_log.py` — NDJSON event logging
- `examples/azur-lane/tasks.json` — 12 task definitions with static action sequences
- Three backend implementations (pilot, default/adb, mock) as untyped dicts

## What's missing

- **Backend contract** — currently `dict[str, Callable[..., Any]]`, needs a typed Protocol
- **Resource reading** — `read_resource` action is a no-op. No OCR, no VLM reader.
- **Gesture support** — only basic swipe exists. No parameterized gestures, no pinch, no drag-and-hold.
- **Error recovery** — `error_strategy` field in tasks.json is never read by executor
- **Data collection** — dock census, pagination, equipment reading. Entirely future work.
- **Critical bugs**:
  - repeat/conditional blocks don't propagate state changes between sub-actions
  - Ambiguous locate results have no "state" key — executor can't distinguish "nothing found" from "two candidates"
  - 9 repeated `sys.path.insert` calls
  - Navigate functions are copy-pasted between pilot and default backends

## Open questions

- What should the Backend Protocol look like? (Protocol vs ABC vs keep dict)
- How does the system read resources from the game screen? OCR? VLM? Hardcoded pixel regions?
- Should data collection (dock census, pagination) be a special task type or a separate system?
- How are gestures parameterized? (start, end, duration, curve?)
- Where does collected data live? Database? JSON files?

## Key scripts

| Script | Lines | What it does |
|--------|-------|-------------|
| executor.py | ~805 | Task execution engine, backend wiring, preflight |
| task_model.py | ~130 | Task definition validation |
| resource_model.py | ~120 | Resource store (MVP placeholder) |
| execution_event_log.py | ~130 | Append-only NDJSON event logging |
