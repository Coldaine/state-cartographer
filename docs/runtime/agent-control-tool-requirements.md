# Agent-Facing Emulator Control Tool Requirements

## Purpose

Acceptance criteria for the external control tool that this repo borrows to control one MEmu 9 instance.

This is a tool-selection spec. It does not own VLM semantics, runtime policy, replay, or teacher escalation.

## Current Decision

The repo uses **adbutils + MaaTouch** as the control substrate.

- `adbutils` (Python ADB client) for transport, device management, screenshots
- MaaTouch (Android touch agent from `vendor/bin/MaaTouch/`) for precision input
- ADB screencap for observation frames
- scrcpy for operator/debug visual only — not runtime frames on Windows

MaaMCP and MaaFramework DLLs are not installed and are not the current plan.

See [substrate-and-implementation-plan.md](../plans/substrate-and-implementation-plan.md) for the full decision rationale and implementation steps.

## Core Requirement

The agent must not lose control of the emulator because the control tool is flaky, opaque, or hard to recover.

## Must-Haves

### 1. Single-device attachment
Attach to one explicit ADB serial. No ambiguous device selection. Ownership scoped to one MEmu instance.

### 2. Persistent control surface
The agent can call the control tool repeatedly without re-bootstrap on every step.

### 3. Reliable frame access
Current, decodable screenshots. Not just socket connectivity — real frames.

### 4. Reliable input primitives
Tap, swipe, key, text, back/home. Coordinates explicit and stable.

### 5. Health visibility
Can tell whether device is connected, frames are live, inputs succeed, session has stalled.

### 6. Recovery path
Routine recovery (lost ADB session, stale frame surface) without manual intervention.

### 7. Unity-compatible
Must not depend on Android accessibility/XML hierarchy as primary semantics path. Must work when the target is screenshot-driven.

### 8. Local operation
Works locally against the user's MEmu 9 instance. No cloud infrastructure.

## Acceptance Gate

A tool is acceptable if it can:
1. Attach to the intended emulator instance without ambiguity
2. Remain usable across repeated calls
3. Provide current usable frames
4. Inject input reliably
5. Expose enough health/recovery behavior that the agent is not blind when the session degrades
