# MEmu Android Control Stack Plan

> Historical note: this document previously recommended a DroidCast-first capture path. It has been updated to reflect the verified `fb0` finding recorded in [2026-03-24-memu-fb0-capture-proof.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-24-memu-fb0-capture-proof.md).

This document is the concrete current plan for the MEmu integration path.

It answers a narrow question:

- what do we actually need for a working MEmu control stack?
- what has now been directly verified?
- what should remain deferred or excluded?

It intentionally does **not** revive `pilot_bridge` as a target. The previous bridge experiment is useful as prior art, but it is not the plan.

## Recommendation

For the current MEmu path, keep the stack small:

- **ADB** for action dispatch
  - taps
  - swipes
  - key events
  - basic device queries
- **root-backed `fb0` capture** for screenshots on the tested MEmu instance
  - use `adb root`, not `su`
  - use `dd if=/dev/graphics/fb0 ...` to device storage and `adb pull`
  - do not treat naive `exec-out cat /dev/graphics/fb0` as reliable on this image
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
  - useful historical retry and black-frame resilience guidance
- `configs/memu.json`
  - confirms the historical MEmu-side screenshot path pointed at DroidCast and should now be treated as stale configuration truth rather than preferred implementation guidance
- `docs/memory/2026-03-24-memu-fb0-capture-proof.md`
  - authoritative proof that direct `fb0` capture returned a non-black frame from the active Azur Lane session on `127.0.0.1:21513`

The active scripts remain offline utilities, not the live emulator control plane.

## What is now verified

The following facts are now directly verified on `127.0.0.1:21513`:

- `adb root` works on the emulator image
- `su` does not exist on the emulator image
- `/dev/graphics/fb0` is present and readable
- the tested framebuffer reports `1152x864`, `32bpp`, stride `4608`
- on-device `dd` plus `adb pull` produced a full-size, non-black raw frame from the active Azur Lane session
- naive `adb exec-out cat /dev/graphics/fb0` produced a truncated result and should not be treated as the baseline implementation path

These facts are enough to justify a root-backed `fb0` first implementation slice. They do **not** yet prove long-session stability or a full runtime.

## What is still open

- repeated capture stability over a longer session
- final channel-order validation on decoded images
- focus verification and failure handling
- actuation plus post-action verification
- whether the second visible MEmu serial behaves the same way
- whether a different backend becomes necessary on a different emulator image

## What we do **not** need for the first MEmu pass

### scrcpy

scrcpy is **not required** for the current MEmu control plan.

Reason:

- the current MEmu path is now oriented around ADB actions plus verified `fb0` observation on the tested image
- scrcpy is a real transport/control system, but it is a different integration choice
- we should not add it unless we later decide that a scrcpy transport layer is specifically better for a new target or a different emulator profile

### DroidMind

DroidMind is **not required** for the first pass.

It may still be useful later as a reference for:

- an MCP-style Android management facade
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

## Integration shape with MEmu

The simplest useful loop is:

1. connect to the MEmu instance over ADB
2. elevate through `adb root` and wait for device readiness
3. capture a frame from `fb0` via `dd` to device storage and `adb pull`
4. validate the frame is exact-size, decodable, and non-near-black
5. decide the next action
6. dispatch the action through ADB
7. capture again and compare the result

That keeps the responsibilities separate:

- ADB owns actions
- the `fb0` transport owns observation
- the runtime owns state interpretation and retries

## What the plan is really asking for

The current plan should settle these questions before any larger build-out:

- what is the minimum reliable MEmu stack on the tested emulator image?
- which parts are contractual and reusable?
- which parts are research-only references?
- what counts as a valid screenshot?
- what counts as a successful action?
- where do retries live?
- where does state interpretation live?

## Suggested scope for the first implementation slice

The first slice should prove only one thing:

- a single MEmu session can be observed, acted on, and verified repeatedly through the root-backed `fb0` path without relying on previous bridge code

That is enough to establish the capture/action contract.

## Next-step gate

Do not expand into scrcpy, DroidMind, MaaMCP, semantic cache work, or richer runtime architecture until the MEmu observe-act-observe loop is proven and stable on the verified `fb0` path.

If a later phase needs richer transport or automation, those tools can be re-evaluated with a concrete gap to fill.
