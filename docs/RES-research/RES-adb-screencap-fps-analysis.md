# RES: ADB Screencap FPS Analysis

**Date:** 2026-03-25
**Status:** Complete
**Method:** Codebase analysis + measured probe data (n=15 samples, MEmu 127.0.0.1:21503, 1280x720)

## Summary

ADB screencap on MEmu takes ~132ms per call. The hardware ceiling is ~7.6 FPS regardless of sleep intervals. Black frames are caused by OpenGL compositor failures, not capture rate. The optimal strategy differs for stress testing (no sleep) vs production (200-300ms interval).

## Measured Latency

| Metric | Value | Notes |
|--------|-------|-------|
| Warm-frame mean | 131.9ms | sd=10.0ms, CV=8%, n=10 |
| Warm-frame 95% CI | [124.7, 139.1] ms | df=9, t=2.262 |
| Cold-frame mean | 151.5ms | sd=54.1ms, n=5 — first call per session |
| Cold-warm delta | ~19.6ms (15% slower) | Cohen's d=0.50 (medium effect) |
| Max ADB throughput | ~7.6 FPS | 1000/131.9ms |

## Capture Method Latency Comparison

| Method | Latency | Reads From | Black Frame Risk |
|--------|---------|------------|-----------------|
| adb screencap -p | 100-140ms | SurfaceFlinger output | Compositor failure |
| adb screencap nc | 60-100ms | SurfaceFlinger output | Compositor failure |
| aScreenCap | 30-60ms | SurfaceFlinger output | Compositor failure |
| DroidCast | 50-120ms | SurfaceFlinger output | Transport crash + compositor |
| DroidCast_raw | 20-50ms | SurfaceFlinger output | Transport crash + compositor |
| nemu_ipc | 5-20ms | Emulator FB via host DLL | Very low (DLL direct) |
| ldopengl | 5-20ms | Emulator FB via host DLL | Very low (GL readback) |
| scrcpy | 1-16ms | H264 decoded frame | Very low (stream) |
| DXcam (planned) | ~3ms | DXGI host window | Very low (post-GL submit) |

## ALAS Capture Strategy (Empirically Tuned)

ALAS uses a `Timer`-based rate limiter with context-dependent intervals:

| Context | Interval | Effective FPS | Source |
|---------|----------|---------------|--------|
| Navigation (default) | 300ms | ~3.3 FPS | `config_generated.py:41` |
| Navigation (user-tuned min) | 100ms | ~7.6 FPS (ADB-bound) | `screenshot.py:168` |
| nemu_ipc / ldopengl | 100-200ms | 5-10 FPS | `screenshot.py:174` |
| Combat loading | 300-1000ms | 1-3.3 FPS | `screenshot.py:177` |
| In-combat (auto-battle) | 1000ms | 1 FPS | `config_generated.py:42` |
| Login | 1000ms | 1 FPS | `login.py:143` |
| OS fleet walk | 350ms | ~2.9 FPS | `os/fleet.py:278` |
| scrcpy | 100ms | up to 10 FPS | `screenshot.py:190` |

Retry loop: 10 attempts (patched from upstream 2) with 100ms sleep between retries on black/invalid frames. Maximum retry budget: ~1.5s before giving up.

## Black Frame Root Causes

Two distinct mechanisms. Neither is rate-related.

### 1. DroidCast Transport Crash

DroidCast runs an `app_process` HTTP server inside the Android container. The HTTP session drops (`ConnectionError`/`ReadTimeout` at 3s), returning empty bytes that decode as black. The ALAS retry handler calls `droidcast_init()` on connection error. This is a transport bug, not a compositor timing issue. **Fixed by switching capture method.**

### 2. OpenGL Compositor Failure (MEmu)

MEmu uses a software VSYNC at 30fps (33ms period). When MEmu's OpenGL guest-to-host bridge fails to submit a frame, SurfaceFlinger has nothing to composite. **Every Android-side method returns the same black frame** because they all read SurfaceFlinger's output buffer.

Key evidence: ALAS runs at 100ms minimum (3x the 33ms vsync period) and black frames still occur. Slowing down does not help because the failure persists across multiple frame periods — it is a driver-level compositor drop, not a millisecond-scale race condition.

Only host-side methods (nemu_ipc, ldopengl, scrcpy, DXcam) bypass this because they read the emulator's framebuffer directly, after the GL submit.

## The Sleep Question

### Why added sleep is pointless for ADB screencap

ADB screencap takes ~132ms to return. Adding any sleep creates dead time without protective benefit:

| Sleep | Total Cycle | Effective FPS | Throughput Loss |
|-------|-------------|---------------|-----------------|
| 0ms | 132ms | 7.6 FPS | 0% (hardware ceiling) |
| 50ms | 182ms | 5.5 FPS | 27% |
| 100ms | 232ms | 4.3 FPS | 43% |
| 200ms | 332ms | 3.0 FPS | 60% |

The ADB round-trip is the natural rate limiter. No additional backpressure is needed.

For faster methods (nemu_ipc at 5-20ms, scrcpy at 1-16ms), sleep IS meaningful because without it you'd poll at 50-200 FPS, causing frame duplication (reading the same composited frame twice) and potential DLL call starvation.

### Optimal rate by use case

| Use Case | Recommended Interval | Rationale |
|----------|---------------------|-----------|
| Stress testing | 0ms (capture-bound) | Maximize frame density; provoke failures; measure true throughput |
| Production observation | 200-300ms | Azur Lane transitions take 200-500ms; 3-5 FPS catches every state; reduces ADB pressure |
| Combat monitoring | 500-1000ms | Nothing to observe during auto-battle; save resources |
| Burst diagnostics | 0ms, 5-10 frames | Quick health probe; check for immediate failures |

## Implications for the Runtime

1. **ADB screencap at ~7.6 FPS is sufficient** for the observation layer. Azur Lane's meaningful state transitions (screen changes, popup appearances, button state changes) take 200-500ms. Even at 3.3 FPS every transition is captured.

2. **Black frames are not fixable by rate tuning.** The planned DXcam + PrintWindow host-side capture shim is the correct architectural fix. Until then, the ALAS retry pattern (10 attempts, 100ms backoff) is the right mitigation.

3. **The stability trap** (documented in `RES-stability-trap-analysis.md`) is real: if the controller requires N consecutive valid frames and captures are sparse, streaks reset and the bot never acts. This argues for maximizing frame density in the observation pipeline — which means using the fastest available capture method (nemu_ipc > scrcpy > aScreenCap > adb), not slowing down ADB.

4. **The stress test should run at 0ms sleep** to establish the true failure rate under maximum load. A separate production-cadence mode (200ms) tests the realistic operating envelope.

## Data Sources

- Probe sessions: `data/events/memu-transport/` (5 sessions, 15 frames)
- ALAS screenshot code: `vendor/AzurLaneAutoScript/module/device/screenshot.py`
- ALAS rate limiter: `vendor/AzurLaneAutoScript/module/base/timer.py`
- ALAS config defaults: `vendor/AzurLaneAutoScript/module/config/config_generated.py`
- Black frame analysis: `docs/memory/project_droidcast_fix.md`, `docs/memory/project_memu_opengl.md`, `docs/memory/project_host_capture_plan.md`
- Substrate plan: `docs/plans/substrate-and-implementation-plan.md`
- Vendor patches: `docs/ALS-reference/ALS-live-ops.md`
