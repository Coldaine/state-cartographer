# Borrowed Control Tool Setup

## Purpose

Define the local setup, roles, and compatibility spike for the borrowed emulator control tools.

This document is operational, not architectural.
It exists to support local intake and validation of:

- `MaaMCP` as the primary agent-facing control tool
- `scrcpy` as the accepted operator/debug visual substrate
- `adbfriend` as a separately installed utility, not part of the runtime path

See also:
- [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)
- [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)

## Decision Status

The substrate posture is currently accepted as the working direction:

- `MaaMCP` for primary agent-facing control
- `scrcpy` as the accepted operator/debug visual substrate
- `adbfriend` as a separate installed utility

This document does not casually reopen that decision.
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
  - accepted operator/debug visual substrate
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

## Substrate Candidate Evaluation

The 2026-03-25 live probe confirmed what candidate research predicted. Evaluated candidates against: Unity-first game UI fit, observation path, input path, maintenance signal.

| Candidate | Unity-first fit | Observation | Input | Maintenance | Verdict |
|---|---|---|---|---|---|
| `MaaMCP` | strong | screenshot + OCR + pipeline | click/swipe/text/key | active | **primary agent-facing surface** |
| `MaaFramework` | strong | multiple screenshot, image-first | multiple input modes | active | **underlying engine** |
| `scrcpy` | medium | live video mirror | HID-style control | active | **debug/operator visual only** |
| `py-scrcpy-client` | medium | wrapper around scrcpy stream | wrapper around scrcpy | maintained | helper only |
| `AndroidViewClient` | limited | screenshot + hierarchy | coordinate/view | active enough | helper/diagnostic |
| `uiautomator2` | weak for game UI | hierarchy/XML-first | element + coordinate | active | helper/diagnostic |
| `Maestro` | medium for app testing | screenshots + assertions | YAML flow | active | not primary |
| `appium-uiautomator2-driver` | weak for Unity gameplay | WebDriver/hierarchy | WebDriver actions | active | reject |
| `minicap` | partial only | legacy lossy capture | none | stale | reject |
| `minitouch` | partial only | none | legacy input daemon | stale | reject |

### Why Maa wins

1. **Matches the problem shape.** Unity-first game means XML hierarchy is at best a helper signal. Image-first automation is the correct default. MaaMCP explicitly exposes screenshot, OCR, click, swipe, key, and pipeline monitoring to an AI agent.

2. **Already confirmed by live probe.** The 2026-03-25 run proved: ADB serial reachability worked, fallback control worked, screenshot capture worked at 1280x720 in ~100ms, tap/swipe/key/text all passed.

3. **Keeps repo code where it belongs.** The repo owns: config, readiness classification, event persistence, action planning. The repo should not own custom screenshot backends or touch injection stacks.

### Why scrcpy is debug_only on Windows

scrcpy on Linux can output to V4L2 (Video4Linux2), which exposes the video stream as a kernel-level device other programs can consume programmatically. This is Linux-only — V4L2 is a Linux kernel API with no Windows equivalent. The maintainer confirmed in Feb 2024: *"No"* (for Windows).

On this Windows + MEmu setup, scrcpy is excellent for operator visibility and debug recording. It cannot serve as the runtime frame source.

### Why other candidates lose

- **uiautomator2 / Appium**: XML/accessibility-tree-first. Correct for native apps, wrong for Unity-rendered games where hierarchy is unreliable.
- **Maestro**: YAML-flow-first. Good for scripted app testing, not the right model for image-driven agent control.
- **minicap / minitouch**: Legacy split-surface daemons. Stale, operationally dated, poor fit as a modern substrate choice.

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
