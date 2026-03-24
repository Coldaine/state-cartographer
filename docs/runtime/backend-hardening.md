# Backend Hardening

> Historical note: this document was previously `docs/execution/EXE-backend-hardening.md`. It now also absorbs the salvage guidance that was split into `pilot-bridge-rework.md`.

## Purpose

Retain the backend lessons learned from live emulator work without pretending there is a supported runtime path today.

See also:
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- [ALS-live-ops.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-live-ops.md)
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)

## Current Status

These backend requirements remain valuable design constraints.

They do **not** imply that the current repo ships a supported live backend.

`quarantine/scripts/pilot_bridge.py` holds the last major backend experiment. It is retained for salvage, not operation.

## Failure Model

A live backend is not one thing. It is at least four layers:

1. ADB transport health
2. port-forward ownership and reconciliation
3. automation plane health
4. screenshot plane health

A healthy device connection is not the same thing as a healthy observation path.

## Requirements To Keep

- serial-scoped ownership of connection and recovery state
- explicit forward reconciliation rather than blind forward spraying
- proof of observation, not just proof of socket connectivity
- narrow recovery ladders before full restarts
- separation between backend concerns and game-specific recovery logic

## Lessons To Preserve

- screenshot health must be tested independently of transport health
- emulator and render-stack assumptions must be documented, not buried in ad hoc code
- bridge code should not absorb game-specific popup logic
- backend readiness should be proven by real frame capture
- coexistence with another operator process can be a real issue and should be designed explicitly, not assumed away

## Bridge Salvage Rules

What is worth salvaging from the quarantined bridge path:
- narrowly scoped screenshot capture
- narrowly scoped tap and swipe execution
- explicit backend readiness checks
- environment-specific notes about emulator, renderer, and screenshot transport behavior

What should not live in a bridge:
- game-specific popup handling
- assignment-specific recovery routines
- runtime policy decisions
- broad control-plane assumptions about what the caller is trying to do

## Criteria To Re-Earn Bridge Code

Before `pilot_bridge.py` or any successor leaves quarantine, it must prove:
- the intended emulator and render stack is correct and documented
- screenshot capture is real, current, and decodable
- tap and swipe actions are verified on the intended setup
- failure and recovery behavior are reproducible
- the bridge is generic transport and observation infrastructure, not embedded game logic

## What This Document No Longer Claims

- there is no supported operator entrypoint described here
- this doc does not certify `pilot_bridge.py` as production-ready
- this doc does not imply the executor path currently exists
