# PilotBridge Rework

> Historical note: this document was previously `docs/execution/EXE-pilot-bridge-rework.md` and assumed `scripts/pilot_bridge.py` was an active execution-layer concern.

## Purpose

Capture what is worth salvaging from `pilot_bridge.py` and what should be discarded if that backend is revisited.

## Current Status

`quarantine/scripts/pilot_bridge.py` is quarantined.

This document is not an endorsement of that file. It is a salvage guide for a future backend owner.

## Useful Knowledge To Preserve

- environment-specific screenshot constraints matter more than abstract backend interfaces
- screenshot capture, tap/swipe, and backend readiness checks should remain narrowly scoped
- coexistence with another operator process can be a real issue and should be designed explicitly, not assumed away

## What Should Not Live In A Bridge

- game-specific popup handling
- assignment-specific recovery routines
- runtime policy decisions
- broad control-plane assumptions about what the caller is trying to do

## Criteria To Re-Earn This Code

Before `pilot_bridge.py` or any successor leaves quarantine, it must prove:

- the intended emulator/render stack is correct and documented
- screenshot capture is real, current, and decodable
- tap/swipe actions are verified on the intended setup
- failure and recovery behavior are reproducible
- the bridge is generic transport/observation infrastructure, not embedded game logic
