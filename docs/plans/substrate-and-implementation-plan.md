# Control Substrate Decision and Implementation Plan

**Date:** 2026-03-25
**Status:** ACTIVE — this is the single authoritative substrate plan

This document answers two questions:
1. What tools does this repo use to control the Android emulator?
2. What code do we write on top of them?

Everything else about substrate selection lives here. There is no second document.

## The Decision

Use **adbutils + MaaTouch + ADB screencap** as the control substrate.

```
Layer 3: MasterStateMachine runtime — workflow, VLM, planning, event logging
Layer 2: MaaTouch (vendor/bin/MaaTouch/) — precision touch over socket
Layer 1: adbutils (pip install adbutils) — Python ADB client
Layer 0: ADB daemon + MEmu Android device
```

**MaaMCP is not installed and is not the plan.**
**MaaFramework DLLs are not installed and are not the plan.**

MaaFramework can be re-added later if the full MAA stack is installed on the machine. Until then, the stack above is what we use.

## Why These Tools

### Why adbutils

`adbutils` is the Python ADB library ALAS already uses (in `vendor/AzurLaneAutoScript/requirements.txt` as `adbutils==0.11.0`). It replaces `subprocess.run(["adb", ...])` entirely. It handles socket reuse, streaming, device listing, forward/reverse management.

### Why MaaTouch

MaaTouch is a self-contained Android touch agent binary already present at `vendor/AzurLaneAutoScript/bin/MaaTouch/maatouchsync`. It provides socket-based touch, multi-point touch, long-click, drag, swipe with acceleration. It runs via `CLASSPATH=... app_process` — no daemon install needed. It replaces `adb shell input tap` which is slow and imprecise.

### Why ADB screencap

`adb exec-out screencap -p` is the universal screenshot fallback. It works on every Android device. On MEmu it produces 1280x720 PNGs in ~100-140ms. Good enough for a VLM-driven agent that captures once per action cycle.

### Why not scrcpy for runtime frames

scrcpy on Linux exposes V4L2 for programmatic frame consumption. V4L2 is Linux-only. On this Windows + MEmu setup, scrcpy is excellent for operator visibility and debug recording. It cannot serve as the runtime frame source.

### Why not uiautomator2 / Appium / Maestro

The target is a Unity-rendered game. XML/accessibility hierarchies are unreliable or empty for Unity UI. These tools are correct for native Android apps, wrong for this game.

### Why not minicap / minitouch

Legacy daemons. Stale maintenance. Incomplete by themselves. MaaTouch is the modern replacement for minitouch.

## The 10-Candidate Evaluation (Summary)

| Candidate | Verdict |
|---|---|
| adbutils | **USE** — Python ADB client |
| MaaTouch | **USE** — precision touch agent |
| MaaFramework | **DEFER** — requires full MAA Windows DLL installation |
| MaaMCP | **DEFER** — requires MaaFramework |
| scrcpy | **DEBUG ONLY** — operator visual, not runtime frames on Windows |
| py-scrcpy-client | Helper only — wraps scrcpy |
| uiautomator2 | Helper/diagnostic only — wrong for Unity |
| AndroidViewClient | Helper/diagnostic only |
| Maestro | Not primary — YAML flow model |
| Appium | Reject — wrong for Unity games |
| minicap | Reject — stale |
| minitouch | Reject — stale, replaced by MaaTouch |

## What ALAS Already Had (and We Ignored)

| ALAS File | What It Does |
|---|---|
| `vendor/.../requirements.txt` | `adbutils==0.11.0` — the library we should have used |
| `vendor/.../module/device/connection.py` | Full ADB session management with retry |
| `vendor/.../module/device/method/maatouch.py` | MaaTouch protocol implementation |
| `vendor/.../module/device/method/adb.py` | Screenshot decode, click, swipe |
| `vendor/.../module/device/screenshot.py` | 9 screenshot methods with fallback |
| `vendor/.../bin/MaaTouch/maatouchsync` | MaaTouch binary |

The ALAS multi-backend pattern (multiple inheritance + method dictionaries for runtime backend selection) is the correct architecture to follow.

## Implementation Steps

### Step 1: Replace subprocess ADB with adbutils

**File:** `state_cartographer/transport/adb.py`

- Import `from adbutils import AdbClient`
- Replace `subprocess.run(["adb", ...])` with `AdbClient.device(serial).shell(...)`
- Lift retry decorator from `vendor/.../module/device/connection.py`
- Lift device listing from `vendor/.../module/device/connection.py`

**Verification:** `python -c "from state_cartographer.transport.adb import ...; ..."` imports clean. Same method signatures.

### Step 2: Add MaaTouch support

**New file:** `state_cartographer/transport/maatouch.py`

- Copy MaaTouch binary from `vendor/.../bin/MaaTouch/maatouchsync`
- Lift protocol from `vendor/.../module/device/method/maatouch.py`
- Adapt to use adbutils socket interface
- Switch input backend to MaaTouch when binary is available, fall back to ADB

**Verification:** Tap via MaaTouch is visible on device. Falls back to ADB if binary missing.

### Step 3: Add screenshot methods

**New file:** `state_cartographer/transport/capture.py`

- Implement `screenshot_adb` via `adb exec-out screencap -p`
- Implement `screenshot_adb_nc` (netcat path) for speed
- Optionally add `nemu_ipc` for MEmu shared-memory path

**Verification:** 5 consecutive captures produce decodable PNGs at 1280x720.

### Step 4: Run live integration tests

- Strengthen assertions: if ADB reachable + device online → tier is OPERABLE or DEGRADED, never UNREACHABLE
- Add `test_maatouch_touch_accuracy`
- Add `test_capture_freshness`
- Remove bare skips

**Verification:** All tests pass against live MEmu. No bare skips.

### Step 5: Clean up naming

- Rename transport files to reflect adbutils+MaaTouch reality
- Update `configs/memu.json` to `"primary_control": "maatouch"`
- Grep for "maamcp" → zero results

## Configuration After Rebuild

```json
{
  "name": "MEmu Player",
  "emulator_type": "memu",
  "adb_serial": "127.0.0.1:21513",
  "primary_control": "maatouch",
  "fallback_observation": "adb_screencap",
  "maatouch_filepath_local": "vendor/AzurLaneAutoScript/bin/MaaTouch/maatouchsync",
  "maatouch_filepath_remote": "/data/local/tmp/maatouchsync"
}
```

## What Repo Code Is Justified

The repo needs code only in the thin layer that existing tools do not own:
- Config loading and pinned-device selection
- Truthful readiness classification (OPERABLE / DEGRADED / UNREACHABLE)
- Structured event persistence to local NDJSON files
- Action correlation IDs, session IDs, artifact references
- Runtime verification logic above primitive clicks and captures
- Workflow-specific recovery policy

The repo does NOT need to compete with adbutils, MaaTouch, or scrcpy at the transport layer.

## Proven vs Still Open

### Proven on pinned MEmu setup (2026-03-25)
- ADB serial reachability
- Repeated screenshot capture at 1280x720 in ~100ms
- Primitive input dispatch (tap, swipe, key, text)
- Reconnect after forced disconnect
- scrcpy attach and debug usefulness

### Still awaiting proof
- MaaTouch deployed and working on this machine
- Long-run burn-in stability
- Cold boot + warm attach + forced reconnect all passing
- Non-trivial text input beyond smoke level

## Success Criteria

1. `subprocess.run` appears zero times in transport code — adbutils used throughout
2. MaaTouch is the primary input backend when available
3. 5 consecutive captures produce valid PNGs
4. Live integration tests pass with no bare skips
5. Health classification is truthful: working fallback = DEGRADED, not FAIL

## Live Probe Evidence

See [2026-03-25-memu-transport-probe-results.md](../memory/2026-03-25-memu-transport-probe-results.md) for the dated evidence from the first probe pass.
