# ADB Backend Hardening Plan

## Goal

Provide a robust, serial-scoped Android control backend for MEmu/Azur Lane that avoids ADB forward congestion, separates transport health from screenshot health, and recovers predictably.

## The real failure model

The backend is not one thing. It is four layers:

1. **ADB transport** — the device serial is reachable and responsive
2. **Port-forward ownership** — local forwarded ports map to the intended device/service
3. **ATX automation plane** — `atx-agent` on port `7912` is alive
4. **Screenshot plane** — DroidCast returns a decodable, current frame

A green `adb devices` line does **not** prove the screenshot pipeline is healthy.

## Root causes found in this repo

### 1. Forward accumulation / ownership ambiguity

Previous logic used repeated `adb forward tcp:0 ...` allocation. Over time this created dozens of stale forwards and made the host-side routing state hard to reason about.

### 2. Silent ADB failures

Several live-control calls did not check `returncode`, so transport failure could look like a higher-level navigation bug.

### 3. Mixed lifecycle ownership

ADB, ATX, and DroidCast recovery were partially managed in different places, with weak guarantees about who owns which port/service.

### 4. Pilot backend first-use fragility

The executor path relied on the pilot bridge being ready, but did not enforce a healthy connected state before use.

## Backend rules going forward

### Rule 1: Single owner per serial

For a given serial, one runtime object owns:

- ADB connectivity checks
- ATX port forward
- DroidCast port forward
- screenshot capture lifecycle
- retry / recovery logic

### Rule 2: Fixed, explicit forwards for the current single-device setup

For this repo's current MEmu setup:

- `tcp:17912 -> tcp:7912` for ATX
- `tcp:53516 -> tcp:53516` for DroidCast

These forwards must be reconciled, not sprayed dynamically.

### Rule 3: Never global-clean forwards in shared mode

Do **not** use `adb forward --remove-all` from runtime code. Remove only forwards that are owned by the current serial/runtime.

### Rule 4: State-changing actions must be serialized per bridge

Screenshot restarts, taps, swipes, and back actions must not interleave on the same bridge instance.

### Rule 5: Every backend must prove observation, not just connection

A connection is only ready when:

- ATX `/info` responds, and
- a real screenshot can be captured and decoded

## Recovery ladder

Recover narrowly, not dramatically:

1. Retry the request once
2. Reconcile forwards
3. Re-check ATX `/info`
4. Restart DroidCast only
5. Reconnect ADB if transport is stale
6. Restart emulator only when lower layers fail repeatedly

## Current implementation status

Implemented in `scripts/pilot_bridge.py`:

- checked ADB commands with timeouts and surfaced failures
- explicit forward ownership checks
- conflict detection for host local ports claimed by another serial
- lazy connect for `screenshot()`, `tap()`, `swipe()`, and `back()`
- bridge-level locking to serialize state-changing operations
- shared DroidCast fast path with fallback to self-managed restart

Implemented in `scripts/adb_bridge.py`:

- default subprocess timeout
- explicit timeout error surfacing

Validated:

- targeted test suite passes
- live smoke test against MEmu succeeds
- owned ATX/DroidCast forwards remain stable after repeated captures

Note: auxiliary forwards such as `localabstract:minitouch` may legitimately appear when ATX/uiautomator2 spins up helper services. Those are not the same failure mode as uncontrolled `tcp:0` forward accumulation.

## Known remaining improvements

### Medium priority

- pass real session context into live `locate()` calls during executor waits/asserts
- unify raw ADB screenshot vs DroidCast backend selection behind a capability-based policy
- add structured backend metrics (forward count, restart count, last good screenshot timestamp)

### Lower priority

- move toward a dedicated serial-scoped `ConnectionManager` abstraction shared by executor/observe/siphon
- support dynamic local port allocation if multi-device orchestration becomes a real requirement

## Operational checklist

Before a live piloting run:

- verify emulator serial is correct
- verify only expected forwards exist for the serial
- verify ATX responds on `tcp:17912`
- verify a screenshot round-trip succeeds

If screenshots go black again:

- inspect `adb forward --list`
- confirm the expected ATX and DroidCast forwards still exist
- check whether ALAS is sharing DroidCast or whether the bridge should restart it
- only then blame the emulator, the moon, or fate
