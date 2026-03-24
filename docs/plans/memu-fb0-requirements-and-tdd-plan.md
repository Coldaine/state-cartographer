# MEmu `fb0` Requirements And TDD Plan

## Purpose

This document defines the next runtime slice in requirements-first terms.

It exists to answer a narrow question:

- how do we turn the verified MEmu `fb0` proof into a minimal implemented transport and observe-act-verify slice without overbuilding the runtime?

See also:
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [end-to-end-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/end-to-end-plan.md)
- [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md)
- [backend-hardening.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/backend-hardening.md)
- [2026-03-24-memu-fb0-capture-proof.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-24-memu-fb0-capture-proof.md)

## Verified Baseline

The plan starts from facts already established on `127.0.0.1:21513`:

- `adb root` works
- `su` does not exist
- `/dev/graphics/fb0` is readable
- framebuffer metadata reports `1152x864`, `32bpp`, stride `4608`
- `dd` to device storage plus `adb pull` produced a complete non-black frame
- naive `exec-out cat /dev/graphics/fb0` was truncated and is not the baseline implementation path

This is enough to justify implementation of a transport slice.
It is not enough to claim a supported live runtime yet.

## Scope

This plan covers only the first thin runtime slice:

- serial-scoped MEmu transport bootstrap
- framebuffer capture
- local decode and frame-health checks
- a minimal observe -> act -> verify loop using fixed or stubbed action choice

This plan does **not** cover:

- semantic cache
- multi-tier VLM routing
- teacher/escalation design
- broad workflow automation
- OCR pipelines
- production replay or retrieval

## Requirements

### R1. Rooted Transport Bootstrap

The transport must:

- target a specific ADB serial
- enable root through `adb root`
- wait for device readiness after the root transition
- fail clearly if the device does not return

Acceptance evidence:

- an integration test or smoke script shows root bootstrap succeeding on the intended serial

### R2. Framebuffer Metadata And Size Discipline

The transport must:

- read or encode the active framebuffer dimensions and byte layout for the target instance
- compute expected frame size from width, height, and bytes per pixel
- reject any capture whose length does not match the expected size

Acceptance evidence:

- a test proves truncated captures are rejected
- a live smoke run shows exact-size capture on the intended device

### R3. Reliable Capture Path

The transport must use the verified reliable capture path:

- `dd if=/dev/graphics/fb0 ...` to device storage
- `adb pull` to local storage

It must not treat direct `exec-out cat /dev/graphics/fb0` as the baseline path on this emulator image.

Acceptance evidence:

- a live smoke run produces at least one exact-size raw capture and decodable image

### R4. Decode Contract

The transport must:

- decode raw framebuffer bytes into an image array usable by downstream code
- keep channel order explicit rather than hidden in assumptions
- validate whether the tested image is BGRA or RGBA before treating the decode as settled

Acceptance evidence:

- a validation run saves decoded images and records which channel order is correct for the tested device

### R5. Frame Health Checks

The first slice must detect transport-level bad outputs, including:

- truncated frame
- black frame
- near-black frame
- repeated frame
- stale frame

Acceptance evidence:

- tests cover the health-check logic on fixture arrays or synthetic frames
- a live run records healthy frames on the intended device

### R6. Focus Awareness

The slice must verify whether Azur Lane is focused before acting.

Acceptance evidence:

- a check against `dumpsys window windows` returns whether `com.YoStarEN.AzurLane` is focused
- loss of focus is surfaced as a typed failure, not silent continuation

### R7. Minimal Action Execution

The first action plane must stay narrow:

- ADB tap is enough for the first slice
- coordinates must be interpreted against the actual framebuffer dimensions (`1152x864`)
- action selection may be fixed or stubbed for the first loop

Acceptance evidence:

- one observed tap is dispatched on the intended device

### R8. Post-Action Verification

The first loop must verify that acting changed something observable.

The minimum acceptable proof is:

- capture pre-action frame
- dispatch one action
- capture post-action frame
- compute frame delta or a comparable measurable difference

Acceptance evidence:

- at least one live observe -> act -> verify run records a measurable frame change

### R9. Generic Boundary

The transport layer must stay generic transport and observation infrastructure.

It must not absorb:

- game-specific popup handling
- workflow policy
- long-horizon runtime orchestration

Acceptance evidence:

- module boundaries keep transport separate from runtime policy and game logic

## Test-Driven Work Order

### Step 1. Define Typed Failure Surface First

Write the failure taxonomy before transport code.

Minimum transport and loop failures:

- `STREAM_TRUNCATED`
- `STREAM_BLACK_FRAME`
- `STREAM_NEAR_BLACK_FRAME`
- `STREAM_REPEATED_FRAME`
- `STREAM_STALE_FRAME`
- `STREAM_FOCUS_LOST`
- `POST_ACTION_NO_STATE_CHANGE`

Tests first:

- enum or typed result tests proving these outcomes are representable and stable

### Step 2. Write Fixture-Level Transport Tests

Before live-device code is relied on, add tests for:

- expected frame-size calculation
- truncated buffer rejection
- decode-path shape and dtype
- black and near-black detection
- frame-delta calculation

These tests can use synthetic byte buffers and small fixture arrays.

### Step 3. Write Command-Sequence Tests

Wrap ADB command execution in a narrow seam that can be faked in tests.

Test that the transport issues:

1. `adb root`
2. `adb wait-for-device`
3. `adb shell dd if=/dev/graphics/fb0 ...`
4. `adb pull ...`

before live-device validation is attempted.

### Step 4. Implement The Thin Transport

Only after Steps 1-3 should the actual transport module be written.

Minimum module responsibilities:

- root bootstrap
- capture
- decode
- cleanup of temporary remote and local files
- optional focus check

### Step 5. Run Live Smoke Validation

Required live checks:

1. capture one frame and save a PNG
2. confirm Azur Lane is visible
3. confirm channel order is correct
4. run repeated capture for a bounded sample

First live gate:

- 20 consecutive exact-size, decodable, non-near-black frames

### Step 6. Add The Minimal Observe-Act-Verify Loop

Only after the transport smoke gate passes:

- capture
- choose a fixed or stubbed tap
- execute tap
- capture again
- compute delta
- emit typed success or failure

Second live gate:

- at least one tap produces a measurable post-action frame change

### Step 7. Only Then Expand Upward

Only after the second live gate passes should the repo proceed to:

- real local VLM routing
- semantic cache work
- richer retry and escalation logic

## Deliverables

The first implementation slice should produce:

- a transport module for the tested MEmu instance
- tests for sizing, decode, and frame-health behavior
- a smoke validation script or equivalent command
- one saved validation image
- one minimal observe -> act -> verify script or entrypoint
- a short results note documenting whether channel order and repeatability gates passed

## Exit Gates

This plan is successful when:

- the transport code matches the verified `fb0` path rather than the old DroidCast assumption
- transport failures are typed and testable
- the tested device yields repeated exact-size decodable frames
- channel order is explicitly validated
- one action is executed and verified through observable frame change

Until those gates are passed, broader runtime architecture remains downstream planning, not active implementation.
