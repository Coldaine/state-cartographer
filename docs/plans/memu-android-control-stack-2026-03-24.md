# MEmu Android Control Stack Proposal

This document is the concrete proposal for the MEmu integration path.

It answers a narrow question:

- what do we actually need for a working MEmu control stack?
- what should be reused from the current repo?
- what should remain deferred or excluded?

It intentionally does **not** revive `pilot_bridge` as a target. The previous bridge experiment is useful as prior art, but it is not the plan.

## Recommendation

For the current MEmu path, keep the stack small:

- **ADB** for action dispatch
  - taps
  - swipes
  - key events
  - basic device queries
- **DroidCast** for screenshots on MEmu DirectX
  - this is the capture backend that matches the current emulator reality
  - use it only as the observation plane, not as the whole runtime
- **Current repo docs and ALAS prior art** for contracts and failure handling
  - observation contracts
  - workflow inventory
  - recovery heuristics
  - vendor patches and emulator notes

## What we should reuse

The useful reuse is mostly architectural and contractual, not a direct code transplant:

- `docs/runtime/observation-contracts.md`
  - good shape for what the model should receive and return
- `docs/workflows/azur-lane-workflows.md`
  - useful task taxonomy and state/substate framing
- `docs/ALS-reference/ALS-live-ops.md`
  - useful recovery rules and operational hard constraints
- `docs/vendor-patches/alas-memu-observation-snapshot-2026-03-19.patch`
  - useful retry and black-frame resilience guidance
- `configs/memu.json`
  - confirms the MEmu-side screenshot path currently points at DroidCast

The active scripts remain offline utilities, not the live emulator control plane.

## What we do **not** need for the first MEmu pass

### scrcpy

scrcpy is **not required** for the current MEmu control plan.

Reason:

- the current MEmu path is already oriented around ADB actions plus DroidCast observation
- scrcpy is a real transport/control system, but it is a different integration choice
- we should not add it unless we later decide that a scrcpy transport layer is specifically better for a new target or a different emulator profile

### DroidMind

DroidMind is **not required** for the first pass.

It may still be useful later as a reference for:

- an MCP-style Android management façade
- device/app/file/shell orchestration patterns
- operator-facing tooling

But the MEmu plan does not need it to prove the basic observe-act-observe loop.

### MaaMCP / MAA

MaaMCP is **not required** for the first pass.

Its useful ideas are deferred to a later stage if and when we need:

- OCR-heavy flows
- pipeline orchestration
- reusable automation chains

For the MEmu proposal, those are nice-to-have later, not day-one dependencies.

## Why DroidCast is still in the plan

DroidCast stays in the proposal because it addresses the actual emulator constraint we have right now:

- MEmu DirectX does not reliably give us usable standard screenshots
- the ALAS/MEmu prior art points to DroidCast as the working capture path
- this is about observation, not about building a new general-purpose control framework

So DroidCast is not here because it is elegant; it is here because it is the current working answer for capture on this emulator path.

## Integration shape with MEmu

The simplest useful loop is:

1. connect to the MEmu instance over ADB
2. capture a frame via DroidCast
3. validate the frame is non-blank and usable
4. decide the next action
5. dispatch the action through ADB
6. capture again and compare the result

That keeps the responsibilities separate:

- ADB owns actions
- DroidCast owns observation
- the runtime owns state interpretation and retries

## What the proposal is really asking for

The proposal should settle these questions before any larger build-out:

- what is the minimum reliable MEmu stack?
- which parts are contractual and reusable?
- which parts are research-only references?
- what counts as a valid screenshot?
- what counts as a successful action?
- where do retries live?
- where does state interpretation live?

## Suggested scope for the first implementation slice

The first slice should prove only one thing:

- a single MEmu session can be observed, acted on, and verified repeatedly without relying on previous bridge code

That is enough to establish the capture/action contract.

## Next-step gate

Do not expand into scrcpy, DroidMind, or MaaMCP until the MEmu observe-act-observe loop is proven and stable.

If a later phase needs richer transport or automation, those tools can be re-evaluated with a concrete gap to fill.