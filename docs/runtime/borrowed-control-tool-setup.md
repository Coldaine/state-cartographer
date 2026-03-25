# Borrowed Control Tool Setup

## Purpose

Define the local setup, roles, and compatibility spike for the borrowed emulator control tools.

This document is operational, not architectural.
It exists to support local intake and validation of:

- `MaaMCP` as the primary agent-facing control tool
- `scrcpy` as the preferred live visual/debug substrate
- `adbfriend` as a separately installed utility, not part of the runtime path

See also:
- [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)
- [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)

## Decision Status

The substrate posture is already decided:

- `MaaMCP` for primary agent-facing control
- `scrcpy` as the preferred live visual/debug substrate
- `adbfriend` as a separate installed utility

This document does not reopen that decision.
Its job is to make the next step operationally clear:

- install the chosen tools locally
- validate them on the pinned MEmu instance
- determine whether `scrcpy` is usable as the runtime observation path or only as the debug/operator stream

That compatibility spike was executed on `2026-03-25`.
Current machine verdict:

- pinned serial: `127.0.0.1:21503`
- control path: Maa/ADB fallback accepted
- runtime observation path: `maamcp_screenshot`
- `scrcpy`: `debug_only` on this Windows setup

## Tool Roles

- `MaaMCP`
  - primary agent-facing control surface
  - attach to the pinned MEmu instance
  - provide screenshot, tap, swipe, key, and text primitives
  - expose health/status if available
- `scrcpy`
  - preferred live visual substrate
  - first use is attach proof and operator/debug visibility
  - runtime observation may use it only if the compatibility spike proves a consumable frame path
- `adbfriend`
  - installed separately for independent Android and ADB workflows
  - not a runtime dependency
  - not part of the first runtime adapter surface

## Local Baseline

The pinned emulator path is currently described in:

- [memu.json](/mnt/c/Users/pmacl/.codex/worktrees/4587/MasterStateMachine/configs/memu.json)

Current default serial in local config:

- `127.0.0.1:21503`

Any borrowed control tool used for the runtime must target that pinned instance explicitly.

## Local Setup Notes

The repo does not vendor these tools.
Local setup should record:

- executable path or installation method
- expected startup command
- pinned serial argument or config
- any local port or endpoint the tool exposes

At minimum, capture:

- `MaaMCP` executable or launcher path
- `scrcpy` executable path
- `adbfriend` executable path

## Compatibility Spike

This spike has already been run for the current machine.
Keep the gate below as the acceptance shape for future revalidation, not as an unexecuted task.

### MaaMCP gate

Pass criteria:

- attach to the pinned MEmu serial without ambiguity
- capture repeated screenshots successfully
- prove screenshots are current and decodable
- execute repeated tap, swipe, key, and text actions successfully
- recover from one forced disconnect or restart without repo code changes

### scrcpy gate

Pass criteria:

- attach to the same pinned MEmu session
- remain stable while `MaaMCP` is also attached
- prove whether `scrcpy` offers a runtime-consumable frame path or only operator-visible mirroring

### adbfriend gate

Pass criteria:

- install and run successfully for separate use
- document the working local command shape

`adbfriend` is not part of the runtime rebuild gate.

## Decision Gate

After the spike, choose the observation path like this:

- if `scrcpy` provides a reliable consumable frame path on MEmu 9:
  - use `scrcpy` for observation
  - use `MaaMCP` for control primitives
- if `scrcpy` is only useful for viewing/debug and not reliable for runtime frame consumption:
  - keep `scrcpy` as the preferred operator/debug stream
  - use `MaaMCP` screenshot access as the runtime observation path for the next slice
  - document that as a degraded but accepted first implementation

This is the only intended branch point for substrate selection in the current rebuild.

## Current Recorded Outcome

- `bootstrap` and `doctor` proved `adb` plus `scrcpy` discovery and confirmed the device was online
- `doctor` still reported `fail` because native MaaFramework tooling was not installed locally
- the transport slice still passed in practice because `MaaAdapter` fell back to direct ADB control
- Maa probe passed repeated capture, input, and reconnect checks
- scrcpy probe attached and coexisted with Maa control, but failed the programmatic frame-path test
- accepted next-slice posture:
  - control via Maa/ADB
  - observation via Maa screenshot capture
  - `scrcpy` for operator/debug visibility only
