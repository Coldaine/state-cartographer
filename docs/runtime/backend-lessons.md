# Backend Lessons

## Purpose

Lessons learned from live emulator work. These are design constraints for the next transport implementation.

## Failure Model

A live backend is four layers, not one:

1. ADB transport health — is the device reachable?
2. Session management — is the adbutils connection alive?
3. Control surface health — is MaaTouch responding? Is ADB input working?
4. Observation health — are screenshots current and decodable?

A healthy device connection is not the same as a healthy observation path.

## Requirements

- Serial-scoped ownership of connection and recovery state
- Explicit reconnection rather than blind retry spraying
- Proof of observation (real frame capture), not just proof of socket connectivity
- Narrow recovery ladders before full restarts
- Separation between transport concerns and game-specific recovery logic

## Lessons

- Screenshot health must be tested independently of transport health
- Emulator and render-stack assumptions must be documented, not buried in code
- Transport code must not absorb game-specific popup logic
- Backend readiness must be proven by real frame capture
- Coexistence with another operator process (scrcpy) must be designed explicitly

## What Belongs in Transport Code

- Narrowly scoped screenshot capture
- Narrowly scoped tap and swipe execution
- Explicit backend readiness checks
- Environment-specific notes about emulator behavior

## What Does NOT Belong in Transport Code

- Game-specific popup handling
- Assignment-specific recovery routines
- Runtime policy decisions
- Broad control-plane assumptions about caller intent

## Criteria For New Transport Code

Any new transport implementation must prove:
1. The intended emulator and render stack is correct and documented
2. Screenshot capture is real, current, and decodable
3. Tap and swipe actions are verified on the intended setup
4. Failure and recovery behavior are reproducible
5. The code is generic transport infrastructure, not embedded game logic
