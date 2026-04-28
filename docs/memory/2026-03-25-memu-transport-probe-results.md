# MEmu Transport Probe Results — 2026-03-25

## Purpose

Retain the dated transport verdict from the first live probe pass against the pinned MEmu instance.

See also:
- [todo.md](/mnt/d/_projects/MasterStateMachine/docs/todo.md)

## Environment

- date: `2026-03-25`
- pinned serial (current tracked config): `127.0.0.1:21503`
- note: some earlier local probes and stale docs referenced `127.0.0.1:21513` on a different MEmu instance index
- tracked config: [memu.json](/mnt/d/_projects/MasterStateMachine/configs/memu.json)
- Historical CLI wrapper: `scripts/memu_transport.py` (deleted)

## Observed Results

### 1. Tool discovery and doctor

- `adb` was found and reachable
- `scrcpy` was found and attachable
- `maafw` / native MaaFramework tooling was not installed locally
- `doctor` returned `verdict=pass` with `readiness_tier=degraded` due to missing preferred Maa stack, even while the device was online and ADB was healthy

### 2. Maa control path

- `MaaAdapter` succeeded via ADB fallback
- repeated screenshot capture passed
- three captures succeeded at `1280x720`
- observed capture times were about `100-140 ms`
- tap, swipe, key, and text all passed
- forced disconnect plus reconnect passed

### 3. scrcpy observation path

- `scrcpy` attached successfully to the same session
- coexistence with active Maa control passed
- programmatic frame-path probe failed on this Windows setup
- observation verdict: `debug_only`

### 4. Combined session verdict

- full session probe verdict: `pass`
- accepted near-term posture:
  - control: Maa/ADB path
  - runtime observation: ADB screencap via adbutils
  - operator/debug stream: `scrcpy`

## Implications

- The transport slice is proven enough to support the next thin runtime layer.
- The next runtime slice should use Maa screenshot capture for machine-consumable observation on this machine.
- `scrcpy` should remain attached for operator visibility and debugging, not as the primary runtime frame source.
- Native `maafw` installation remains useful, but it is no longer the blocker for transport proof on this setup.
