# ADB / Emulator Live Testing Plan

Status: active testing plan for the borrowed Android control substrate.

This document defines how the repo should test ADB-connected emulator control, frame capture, recovery, heartbeat behavior, and local evidence persistence.

It follows the repo testing rule:
- no mocks for the authoritative proof
- prefer live integration and real artifacts
- keep pure-code tests only where they validate stable model or serialization logic

See also:
- [testing-strategy.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testing-strategy.md)
- [substrate-and-implementation-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/substrate-and-implementation-plan.md)
- [health-heartbeat-logging.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/health-heartbeat-logging.md)
- [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)

## Purpose

Answer one practical question:

**How do we prove the Android control substrate is real, current, recoverable, and observable on the pinned MEmu setup without hiding behind mocks?**

## What this plan covers

This plan covers live validation of:
- pinned-serial reachability
- borrowed control-surface availability
- frame capture and freshness
- primitive input dispatch
- action acknowledgement
- recovery ladder behavior
- heartbeat and readiness classification
- local file logging and artifact persistence

It does not define gameplay semantics or VLM task evaluation.

## Test stance

### The authoritative proof is live

The authoritative proof for this repo must come from live tests against the pinned emulator serial.

If a test claims that:
- the device is reachable
- frames are fresh
- actions land
- degraded posture is classified correctly

then that claim should be backed by a real MEmu session and real evidence files.

### Pure-code tests are still allowed where they are honest

Pure-code tests remain useful for stable logic such as:
- readiness-tier mapping
- degradation-code serialization
- event-envelope validation
- log path construction
- retention-policy decisions

Those tests are helpers.
They are not substitutes for live proof.

## Test environments

### Primary environment

The default authoritative environment is:
- Windows host
- pinned MEmu instance
- pinned ADB serial from tracked config
- repo-managed transport CLI and runtime glue

### Required test posture

Before running live tests:
- emulator instance must be running
- intended ADB serial must be known and reachable
- emulator render mode and graphics posture should be recorded
- target resolution/orientation should be stable and recorded
- game or target app posture must be safe for reversible checks
- screen state must be captured into local evidence paths
- test run must have a unique session id
- operator-coexistence assumptions (`scrcpy` attached or detached) should be recorded

### Safe action policy

Live tests should prefer:
- reversible navigation actions
- non-destructive taps and back/home checks
- opening and closing menus
- safe launcher/system interactions where available

Avoid:
- destructive purchases or account changes
- actions that consume rare game state without explicit test labeling
- long unattended flows before heartbeat and incident logging are in place

### Repetition requirement before stronger claims

Before promoting a substrate claim from “working once” to “trusted current posture”, require at least:
- one cold-boot run
- one warm-attach run
- one forced disconnect/reconnect run

If those three are not all present, keep the recommendation provisional.

## Required live test families

### 1. Preflight readiness

Goal:
- prove the pinned serial is reachable and classify readiness truthfully

Assertions:
- transport layer reports the correct serial
- device online state is real
- readiness is not collapsed into a single misleading boolean
- missing preferred tools produce degradation codes, not false transport failure

Evidence:
- tooling events
- readiness summary JSON
- capture artifact if observation is healthy

### 2. Frame capture and freshness

Goal:
- prove frames are decodable and current

Assertions:
- capture succeeds repeatedly
- width/height are plausible
- artifact bytes are non-trivial
- timestamps and frame hashes are persisted
- freshness watchdog flags stale observation rather than silently reusing old evidence

Evidence:
- per-capture tooling events
- saved frames under `data/artifacts/`
- frame summary with hash and capture timestamp

### 3. Primitive action dispatch

Goal:
- prove tap, swipe, key, and text actions can be issued through the chosen surface

Assertions:
- action dispatch returns a structured result
- action event gets a stable `action_id` / `attempt_id`
- failure states are explicit and persisted

Evidence:
- input dispatch events
- tool log slice
- before/after frame refs for any action that is expected to move state

### 4. Action acknowledgement

Goal:
- prove the repo can verify that an action did something, not merely that a subprocess returned success

Assertions:
- tap acknowledgement verifies expected modal/page/button change
- key acknowledgement verifies expected state change or dismissal
- text acknowledgement verifies a non-empty input actually lands when text input is claimed to work
- failed acknowledgement is recorded as failed acknowledgement, not transport failure

Evidence:
- runtime `action_ack` events
- before/after frames
- expected-vs-actual ack fields

### 5. Recovery ladder

Goal:
- prove the repo can survive common substrate degradation

Candidate fault injections:
- disconnect and reconnect ADB session
- kill and reattach borrowed control process
- intentionally request a fresh capture after disruption

Assertions:
- escalation stays scoped to the failing layer first
- recovery events are persisted step-by-step
- successful recovery re-proves the observe/act/observe loop
- failed recovery creates an incident bundle

Evidence:
- recovery step events
- incident or recovery summary
- last-known-good heartbeat snapshot

### 5b. Native/system overlay recovery

Goal:
- prove the repo can handle non-Unity edges such as launcher, permission, crash, or Android-native dialogs

Assertions:
- the test records whether the surface is Unity-rendered or native Android
- helper tools such as `uiautomator2` remain optional helpers rather than hidden primary substrate owners

### 6. Workflow microtests

Goal:
- prove short real workflows can advance one or two safe steps with progress tracking

Examples:
- open a safe menu and return
- dismiss a benign popup
- navigate to one known screen and confirm arrival

Assertions:
- workflow progress heartbeat advances
- no-progress watchdog fires when appropriate
- runtime logs record intent separately from tooling logs

Evidence:
- runtime event stream
- progress summary
- linked tooling events and frames

### 7. Logging and artifact persistence

Goal:
- prove every important move leaves local file evidence

Assertions:
- session ids are unique
- tooling and runtime streams are written separately
- artifacts are referenced from events rather than orphaned
- failed sessions preserve richer evidence than successful ones

Evidence:
- NDJSON streams under `data/events/`
- human-readable logs under `data/logs/`
- screenshots and other artifacts under `data/artifacts/`

## Suggested test structure

Use explicit test families instead of one giant magic test.

Suggested markers:
- `live_adb`
- `live_transport`
- `live_capture`
- `live_ack`
- `live_recovery`
- `live_workflow`
- `live_logging`

Suggested split:
- `tests/live/test_transport_readiness.py`
- `tests/live/test_frame_freshness.py`
- `tests/live/test_input_ack.py`
- `tests/live/test_recovery_ladder.py`
- `tests/live/test_workflow_microsteps.py`
- `tests/live/test_event_logging.py`

These do not all need to exist immediately.
But this is the target shape.
The current first-pass live smoke coverage lives under `tests/transport/` and can be split out later once the suite grows beyond transport-focused checks.

## Assertions that matter most first

If only a few live tests get written first, prioritize these:

1. **truthful readiness classification**
   - if ADB works and fallback control works, verdict must not be blanket `fail`

2. **fresh frame proof**
   - repeated frames are captured and timestamped

3. **one safe action acknowledgement**
   - an action can be issued and verified with before/after evidence

4. **one scoped recovery test**
   - a forced disconnect produces a truthful recovery trail

5. **one non-empty text input proof or an explicit downgrade of text confidence**

## Evidence requirements for every live test

This is the target bar for the mature live suite.
The current first-pass smoke tests in `tests/transport/` prove attach/capture/recovery behavior, but they do not yet emit the full evidence bundle below.

Every live test should emit or link:
- `session_id`
- `serial`
- start and end timestamps
- event stream paths
- artifact paths
- summary JSON

A live test that passes without leaving evidence is not a very useful test.
It is just optimism with a badge.

Also: these are local authoritative integration tests for the pinned machine, not a promise that every host or CI environment can reproduce them unchanged.

## Failure handling rules

When a live test fails:
- do not auto-retry endlessly
- do not swallow the first failure behind a “self-healed” pass
- preserve the initial failure evidence
- classify whether the failure is transport, observation, action acknowledgement, or workflow-progress related

When a live test is unsafe to run:
- mark it skipped
- record why it was skipped
- never report skipped live tests as passed

## Relationship to logging design

The logging and heartbeat behavior required by these tests is owned by:
- [health-heartbeat-logging.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/health-heartbeat-logging.md)

This testing plan is the validation companion to that runtime design.

## Near-term execution order

1. Add live readiness classification test
2. Add live frame freshness test
3. Add one safe action acknowledgement test
4. Add one recovery ladder test
5. Add event/log persistence assertions for the same tests
6. Only then expand into longer workflow microtests

## Success condition

This plan is satisfied when the repo can repeatedly demonstrate, on the pinned MEmu setup, that:
- the serial is reachable
- the chosen borrowed substrate can observe and act
- degraded posture is classified honestly
- recovery is auditable
- every important move leaves local file evidence
