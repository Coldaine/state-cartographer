# RES: Frame Ring Buffer Design

**Date:** 2026-03-25
**Status:** Deferred (2026-03-26) — Vulkan eliminated the capture failure mode this was designed for. Design is shelf-ready; revisit if ADB screencap starts failing again. See `docs/decisions.md`.
**Implementation target:** `state_cartographer/transport/frame_ring.py` (if/when needed)

## Problem

The stress test and future runtime need continuous screenshot capture decoupled from consumption. The synchronous pattern (capture → process → sleep → repeat) blocks the capture loop whenever a VLM call takes 1-5 seconds. We need a ring buffer that a capture thread fills continuously while consumers sample at their own pace.

## Design Decision: Pre-allocated Numpy Ring at Half-Res BGRA

Three AI models (Claude benchmarks, Codex GPT-5.4, Gemini 3 Flash) independently converged on the same architecture. No disagreements on the core design.

### Why not PNG bytes in a deque?

PNG compression saves only **3.6%** on game screenshots (3,471 KB vs 3,600 KB raw). Game frames with UI elements, gradients, and text are nearly incompressible. Every consumer read pays a **14ms decode cost**. The append is fast (0.05us) but the read is the bottleneck.

### Why not decoded numpy in a deque?

`deque[numpy].append` requires `frame.copy()` on every insert — **1,019us** per frame due to heap allocation + 3.5MB memcpy. Creates GC pressure on long runs.

### Why pre-allocated numpy ring?

`np.copyto` into a fixed slot: **193us** write, zero heap allocation. One contiguous allocation at startup, never moves. Consumer reads via `.copy()`: **525us**.

### Why 640x360 BGRA, not full-res RGB?

| Choice | Rationale |
|--------|-----------|
| **640x360** (half-res) | 4x memory savings (26MB vs 106MB for 30 frames). VLM page classification doesn't need full-res. Resize costs only +0.77ms via cv2.INTER_AREA. |
| **BGRA** (4 channels) | 4-byte pixels align to 32-bit SIMD registers — fewer cache misses. Convert to RGB for VLM via `frame[:,:,:3]` which is a zero-cost numpy view. |

## Benchmark Data

Measured on Python 3.14.3, numpy 2.4.3, cv2 4.13.0, Windows 11, AMD64.

### Memory Footprint

| Strategy | Per Frame | 30 Frames | 60 Frames |
|----------|-----------|-----------|-----------|
| PNG bytes | 3,471 KB | 99 MB | 203 MB |
| numpy 1280x720 BGRA | 3,600 KB | 106 MB | 211 MB |
| **numpy 640x360 BGRA** | **900 KB** | **26 MB** | **53 MB** |

### Write Latency

| Method | Latency | Notes |
|--------|---------|-------|
| `deque[PNG].append` | 0.05 us | Pointer only — consumer pays 14ms decode |
| **`np.copyto` (pre-alloc)** | **193 us** | Zero heap alloc, fixed address |
| `deque[numpy] + .copy()` | 1,019 us | Heap alloc per frame, GC pressure |
| `shared_memory np.copyto` | 139 us | Overkill for single-process |

### Decode + Resize Pipeline

| Step | Cost |
|------|------|
| `cv2.imdecode` (PNG → numpy) | 14.42 ms |
| `cv2.resize` (1280x720 → 640x360) | +0.77 ms |
| Total per frame | **~15.2 ms** |
| Budget at 7.6 FPS (132ms ADB cycle) | 117 ms headroom |

### Threading

numpy releases the GIL during `np.copyto` — two threads ran 2x500 writes in 76.8ms vs 123.1ms single-threaded (ratio 0.62). True parallelism confirmed on CPython 3.14.

## Implementation

### `state_cartographer/base/frame_ring.py`

```
FrameRing(capacity=30)
├── put(frame_bgra, raw_png)    — producer: decode → resize → np.copyto (193us)
├── latest()                     — consumer: newest frame copy (525us)
├── latest_rgb()                 — newest frame as BGR (drop alpha, view)
├── get(seq)                     — history access by sequence number
├── wait_new(timeout)            — block until new frame (Condition-based)
├── start(source)                — launch background capture thread
├── stop()                       — graceful shutdown
├── anomaly_deque                — deque(maxlen=60) of raw PNG bytes
└── dump_anomaly_preroll(dir)    — save PNG pre-roll to disk for debugging
```

**Key design points:**
- **Monotonic sequence numbers** per slot — readers detect stale data and request by history index
- **`threading.Condition`** — consumers can `wait_new()` instead of polling
- **Backend-agnostic** — any object with `screenshot_png() -> bytes` works (ADB, scrcpy, DroidCast, Win32)
- **Anomaly pre-roll** — raw PNG bytes in a separate deque for instant disk dump without re-encoding (borrowed from ALAS `screenshot_deque` pattern, but intentional rather than error-only)

### Producer Pipeline (in capture thread)

```
ADB.screenshot_png()  →  cv2.imdecode()  →  ensure BGRA  →  cv2.resize(640x360)  →  np.copyto(ring[slot])
      132ms                  14ms              ~0ms              0.77ms                    0.19ms
```

Total cycle: ~147ms per frame = ~6.8 effective FPS. The ADB round-trip (132ms) dominates.

## What This Enables (Next Steps)

### 1. Wire FrameRing into the stress test

Replace the synchronous capture loop in `scripts/adb_stress_test.py` with:
```python
ring = FrameRing(capacity=30)
ring.start(adb)
# VLM consumer samples from ring without blocking capture
while running:
    frame, meta = ring.wait_new()
    # validate, classify, log
ring.stop()
```

**Effect:** Capture never stalls waiting for VLM (1-5s per call). The ring keeps filling at ~6.8 FPS while VLM processes frames at its own pace. Frame density for anomaly detection goes up.

### 2. Use FrameRing as the observation layer for the runtime

The runtime state machine (`executor.py`, future `pilot.py`) currently calls `screenshot()` synchronously on every loop iteration — exactly the ALAS pattern. With the ring:

- State machine calls `ring.latest()` instead of `adb.screenshot_png()` — gets a frame in **525us** instead of **132ms**
- State machine never blocks on ADB I/O
- VLM classifier runs as a separate consumer thread, writing labels back
- The ring provides 4 seconds of history (30 frames / 7.6 FPS) for debugging "what just happened?"

**Effect:** The observation layer becomes async. The state machine runs at whatever speed it can think, not gated by ADB. This is the architectural prerequisite for the multi-tier runtime described in `docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md`.

### 3. Swap capture backend without touching consumers

The FrameRing accepts any `CaptureSource` with `screenshot_png() -> bytes`. When we implement the host-side capture shim (DXcam/PrintWindow, documented in `project_host_capture_plan.md`), the ring doesn't change — only the source does:

```python
ring.start(adb_source)       # today: 6.8 FPS, 132ms
ring.start(scrcpy_source)    # future: 30+ FPS, <50ms
ring.start(dxcam_source)     # future: 60+ FPS, ~3ms
```

Consumers see the same `ring.latest()` API regardless of backend.

### 4. Anomaly pre-roll for debugging

When VLM detects a low-confidence frame or the state machine sees unexpected state:
```python
ring.dump_anomaly_preroll("data/incidents/2026-03-25_stuck/")
```
Saves the last 60 raw PNG frames to disk instantly — no re-encoding, no capture interruption.

## Data Sources

- Ring buffer benchmarks: `.omc/scientist/reports/2026-03-25_ring_buffer_benchmark.md`
- Framebuffer analysis: `.omc/scientist/reports/2026-03-25_1722_framebuffer_capture_analysis.md`
- ADB FPS analysis: `docs/RES-research/RES-adb-screencap-fps-analysis.md`
- CCG tri-model consensus: `.omc/artifacts/ask/codex-...-2026-03-25T23-20-28.md`, `.omc/artifacts/ask/gemini-...-2026-03-25T23-31-58.md`
- ALAS screenshot deque pattern: `vendor/AzurLaneAutoScript/module/device/screenshot.py:114-122`
- Frigate NVR shared memory pattern: [Frigate installation docs](https://docs.frigate.video/frigate/installation/)
