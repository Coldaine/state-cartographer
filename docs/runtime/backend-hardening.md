# Backend Hardening

> Historical note: this document was previously `docs/execution/EXE-backend-hardening.md` and treated backend work as part of the `EXE` domain.

## Purpose

Retain the backend lessons learned from live emulator work without pretending there is a supported runtime path today.

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
- emulator/render-stack assumptions must be documented, not buried in ad hoc code
- bridge code should not absorb game-specific popup logic
- backend readiness should be proven by real frame capture

## What This Document No Longer Claims

- there is no supported operator entrypoint described here
- this doc does not certify `pilot_bridge.py` as production-ready
- this doc does not imply the executor path currently exists
