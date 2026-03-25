# Agent-Facing Emulator Control Tool Requirements

## Purpose

This document defines the requirements for an external control tool that an agent can use to attach to and control a single MEmu 9 instance.

This is a **tool-selection spec**, not a runtime architecture document.

It answers:

- what must already be solved by the external control tool
- what our runtime should borrow instead of rebuilding
- what would disqualify a tool as the control substrate

It does **not** own:

- VLM task semantics
- runtime control policy
- replay design
- teacher escalation

Those remain owned by the runtime plan and runtime code.

## Current Decision Status

The repo has already made the directional substrate decision:

- `MaaMCP` is the primary agent-facing control tool
- `scrcpy` is the preferred live visual/debug substrate
- `adbfriend` is installed separately and is not part of the runtime path

What remains open is not tool selection.
What remains open is operational proof on the pinned MEmu 9 setup:

- whether `MaaMCP` behaves reliably enough in repeated real use
- whether `scrcpy` yields a runtime-consumable frame path or only operator/debug visibility

So this document remains useful as the acceptance spec for that proof step, not as an invitation to reopen tool shopping.

## Core Requirement

The agent must **not lose control of the emulator because the control tool is flaky, opaque, or hard to recover**.

That is requirement zero.

## Scope

The tool is the agent-facing substrate for:

- connecting to one pinned MEmu 9 instance
- maintaining control over time
- exposing frame and input primitives
- surfacing health and failure state
- recovering from routine transport/session breakage

The runtime built on top of it will own:

- observe -> decide -> act -> verify
- VLM prompts and schemas
- action validation
- transition handling
- retry/recovery policy
- replay and teacher governance later

## Must-Haves

### 1. Single-device attachment

The tool must:

- attach to one explicit ADB serial
- avoid ambiguous device selection
- make the selected device visible to the caller
- keep ownership scoped to one MEmu instance

### 2. Persistent control surface

The tool must provide a control surface the agent can call repeatedly without re-bootstrap on every step.

Acceptable surfaces:

- a hardy CLI
- an MCP server

The repo is **not** an MCP architecture project, but MCP is acceptable if it is the most practical agent-facing tool surface.

### 3. Reliable frame access

The tool must expose a frame surface that is good enough for a visual runtime.

Acceptable:

- stable live stream
- stable screenshot API with proven freshness and recoverability

Not acceptable:

- a control tool that only proves socket connectivity but cannot reliably produce current, decodable frames

### 4. Reliable input primitives

The tool must provide:

- tap
- swipe
- key
- text
- back/home equivalents if exposed separately

Coordinate handling must be explicit and stable.

### 5. Health visibility

The tool must make it possible to tell:

- whether the device is connected
- whether the frame surface is live
- whether input commands are succeeding
- whether the session has disconnected or stalled

This may be built in or inferable from structured command results, but it must be available.

### 6. Recovery path

The tool must support routine recovery without manual intervention for common failures such as:

- lost ADB session
- stale or disconnected frame surface
- broken forward/session state

Full automation of every recovery case is not required, but the tool must not force the agent into blind manual guesswork.

### 7. Unity-compatible model

The tool must **not** depend on Android accessibility/XML hierarchy as its primary semantics path.

It may expose those as helper probes.

It must still be usable when the target game is effectively screenshot-driven.

### 8. Local operation

The tool must work locally against the user’s MEmu 9 instance.

It must not require:

- cloud infrastructure
- hosted control planes
- remote device farms

## Strong Preferences

- scrcpy-backed or equivalently strong frame/control substrate
- structured machine-readable outputs
- explicit session/health commands
- clean install and local bootstrap
- active maintenance
- documented MEmu or emulator compatibility
- degraded-mode fallback if the primary frame surface breaks

## Explicit Non-Requirements

The tool does **not** need to provide:

- workflow reasoning
- replay logic
- planner prompts
- semantic state memory
- teacher-model escalation
- project-specific game logic

If a tool tries to own those, that is not a benefit.

## Reject If

Reject a candidate tool if any of these are true:

- it is primarily an XML/accessibility-tree automation tool
- it assumes deterministic replay or pipeline JSON as the main control model
- it is multi-device-first and awkward for a single pinned instance
- it cannot maintain a reliable session without repeated manual resets
- it has poor visibility into frame freshness or session health
- it hides failures behind vague prose instead of actionable results
- it is effectively abandonware

## Practical Selection Question

The selection question is:

**What tool gives the agent the most stable, recoverable, observable control surface over one MEmu 9 instance while leaving runtime intelligence to our code?**

That is the only thing this document is trying to answer.

## Acceptance Gate

A tool is acceptable for the next stage if it can do all of the following on one real MEmu 9 session:

1. attach to the intended emulator instance without ambiguity
2. remain usable across repeated calls from an agent
3. provide current usable frames
4. inject input reliably
5. expose enough health/recovery behavior that the agent is not blind when the session degrades

If it cannot do those five things, it is not the right substrate.
