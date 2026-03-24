# MEmu Transport and Integration Note

This document is the transport/integration companion for the emulator path.

It is not the canonical runtime architecture plan.

For the runtime blueprint, use:
- [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)

For current prototype status, use:
- [tiered-automation-stack.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/tiered-automation-stack.md)

## Purpose

This note answers only these questions:

- how screenshots and actions move through the MEmu path
- what baseline infrastructure is needed before higher-level runtime work
- which emulator-specific constraints shape that path

It does not own tiering policy, semantic cache design, teacher escalation, or runtime architecture sequencing.

## Baseline Recommendation

For the first MEmu path, keep the integration layer narrow:

- `ADB` for connection, shell control, bootstrap, and recovery
- screenshot transport that can be proven stable on the emulator path
  - `DroidCast` is the current baseline mentioned in the near-term plan
  - direct ADB screenshot capture remains a valid comparison or fallback path
- repo runtime/VLM contracts for interpretation above the transport layer

The baseline should prove only an observe-act-observe loop on one MEmu session.

## What This Layer Owns

- device connection and basic health checks
- screenshot acquisition from the emulator
- action dispatch primitives
- emulator-specific bootstrap and recovery commands
- evidence needed to prove a frame/action loop is reliable enough for runtime work above it

## What This Layer Does Not Own

- VLM task semantics
- semantic cache policy
- hit/hint/miss routing
- teacher escalation
- workflow reasoning

Those belong to the canonical runtime plan, not to this transport note.

## Unity Constraint

The target game is Unity-first.

That means structured Android UI hierarchy tooling should not be treated as the semantic layer for the runtime. In particular:

- `uiautomator2` may still be useful for diagnostics or limited Android shell interaction
- it should not be treated as the core observation or semantics path for the live Unity workflow

The runtime must be able to operate from screenshots and action verification rather than assuming a rich accessibility tree.

## Practical Integration Shape

The narrow transport loop is:

1. connect to the MEmu instance over `adb`
2. acquire a usable frame through the selected screenshot transport
3. dispatch a primitive action through `adb`
4. capture again
5. verify that the transport path remains stable enough for the runtime layer above it

This note intentionally stops there.

## Deferred Or Optional Tools

- `scrcpy`
  - useful comparison path if transport stability or latency needs to be evaluated
  - not the semantic owner of the runtime
- `uiautomator2`
  - optional diagnostic/helper tool
  - not the primary semantics path for Unity interaction
- `DroidMind`, `MaaMCP`, and similar orchestration layers
  - deferred until a concrete transport or runtime gap requires them

## Success Gate

This note is satisfied when the emulator path can repeatedly:

- capture usable screenshots
- dispatch actions
- verify that the loop is stable on one real session

Once that gate is met, the canonical runtime plan owns the next architectural step.
