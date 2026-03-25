# MEmu Transport and Integration Note

This document is the borrowed-tool intake note for the emulator path.

It is not the canonical runtime architecture plan.

For the runtime blueprint, use:
- [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)

For the external control-tool selection spec, use:
- [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)

## Purpose

This note answers only these questions:

- which borrowed tools should be used for MEmu 9 attachment and interaction
- what baseline integration is needed before higher-level runtime work
- which emulator-specific constraints shape that path

It does not own tiering policy, semantic cache design, teacher escalation, or runtime architecture sequencing.

## Tool Posture

The borrowed substrate posture is:

- `MaaMCP` is the primary agent-facing control tool for connect, screenshot, tap, swipe, key, text, and health/status if available
- `scrcpy` is the accepted operator/debug stream, not the runtime frame source on this Windows setup
- `adbfriend` is installed and documented separately for your own use, but it is not part of the runtime path

The runtime should borrow these tools rather than reimplementing attachment, capture, and input plumbing.

Observed result from the 2026-03-25 live probe pass:

- Maa/ADB control path is accepted for the current machine
- `scrcpy` attaches and coexists, but is `debug_only` rather than a runtime-consumable frame source on this Windows setup
- the next runtime slice should use Maa screenshot capture for machine-consumable observation

## What This Layer Owns

- device connection and basic health checks
- screenshot/frame access from the emulator path
- action dispatch primitives
- emulator-specific bootstrap and recovery commands
- evidence needed to prove a frame/action loop is reliable enough for runtime work above it

## What This Layer Does Not Own

- VLM task semantics
- semantic cache policy
- hit/hint/miss routing
- teacher escalation
- workflow reasoning

Those belong to the canonical runtime plan, not to this integration note.

## Unity Constraint

The target game is Unity-first.

That means structured Android UI hierarchy tooling should not be treated as the semantic layer for the runtime. In particular:

- `uiautomator2` may still be useful for diagnostics or limited Android shell interaction
- it should not be treated as the core observation or semantics path for the live Unity workflow

The runtime must be able to operate from borrowed control-tool frames and action verification rather than assuming a rich accessibility tree.

## Practical Integration Shape

The narrow integration loop is:

1. connect to the MEmu instance through the borrowed control tool
2. attach the accepted debug visual substrate for operator visibility when useful
3. dispatch primitive actions through the borrowed control tool
4. capture again
5. verify that the loop is stable enough for the runtime layer above it

This note intentionally stops there.

## Deferred Or Optional Tools

- `scrcpy`
  - useful as the accepted visual/debug substrate
  - not the semantic owner of the runtime
- `uiautomator2`
  - optional diagnostic/helper tool
  - not the primary semantics path for Unity interaction
- `DroidMind` and similar orchestration layers
  - deferred until a concrete transport or runtime gap requires them

## Success Gate

This note is satisfied when the emulator path can repeatedly:

- attach to the intended MEmu instance
- capture usable current frames
- dispatch actions
- verify that the loop is stable on one real session

Once that gate is met, the canonical runtime plan owns the next architectural step.
