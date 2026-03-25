# Host-Side Window Capture Shim + Screenshot Pipeline Hardening

**Date:** 2026-03-25
**Status:** DRAFT — ralplan consensus pending
**Branch:** transport/memu-substrate-slice

## Problem Statement

ADB `exec-out screencap -p` returns pure-black 3,669-byte frames on MEmu (OpenGL renderer). This is because all Android-side screenshot methods — ADB screencap, DroidCast, uiautomator2, nemu_ipc — read the same virtual SurfaceFlinger framebuffer. When the emulator hasn't flushed that framebuffer, every method returns black.

ALAS has 10 screenshot methods and a `check_screen_black()` that retries once. It has NO host-side fallback. Our current `capture.py` is a 58-line wrapper around `adb.screenshot_png()` with zero validation.

The user asks two questions:
1. Can we add a host-side window capture shim as a backup?
2. Should we adopt ALAS's pipeline as our hardened backend?

## RALPLAN-DR Summary

### Principles (5)

1. **Framebuffer diversity** — The primary and fallback screenshot methods MUST read from different data sources (Android framebuffer vs host compositor), not just different doors into the same buffer.
2. **On-demand, not continuous** — We capture once per action cycle (~1-2fps), not streaming. Resource overhead must be near-zero when idle.
3. **Validation before consumption** — Every frame must pass pixel-level validation (not just byte count) before entering the VLM pipeline.
4. **No vendor lock-in** — The capture shim must work across emulators (MEmu, LDPlayer, BlueStacks), not be MEmu-specific.
5. **Lift patterns, not codebases** — Cherry-pick ALAS architectural patterns (method dictionary, error-specific retry), don't fork the ALAS codebase.

### Decision Drivers (top 3)

1. **Black frame elimination** — The entire reason we're doing this. ADB screencap returns black on MEmu. The fix must guarantee non-black frames reach the VLM.
2. **Resource weight** — The user explicitly said "hopefully not very heavyweight." DXcam at idle uses ~0 CPU. A continuous scrcpy stream uses meaningful GPU. On-demand host capture is the right budget.
3. **Minimized/hidden window reality** — The user proposed 3 modes (visible, minimized, hidden). Research shows minimized OpenGL/DirectX windows CANNOT be captured by any host-side method including WGC. This constrains the design.

### Viable Options (3)

#### Option A: DXcam DXGI backend — region capture from monitor output
- **How:** `pip install dxcam`. Find window rect via `ctypes.windll.user32.GetWindowRect()`, then `camera.grab(region=(left, top, right, bottom))`. Use `processor_backend='numpy'` to avoid cv2 dependency.
- **Pros:** Fastest Python capture (240fps). Near-zero idle overhead. No per-capture cost — grabs from GPU output. Works with any renderer (OpenGL, DirectX, GDI). Python 3.10-3.14. No extra processes.
- **Cons:** Captures from monitor, not window — if another window overlaps, it captures the overlap. Cannot capture minimized windows. Requires the emulator to be visible on screen. Region must be clamped to monitor bounds for partially off-screen windows.
- **Overhead:** ~0 CPU idle, ~2ms per grab, ~20MB RSS for the camera object.

#### Option B: DXcam WGC backend — window-targeted capture
- **How:** `pip install "dxcam[winrt]"` (same library, `[winrt]` is an extras group that adds WinRT dependencies). Use `dxcam.create(backend='winrt')` to capture a specific window by HWND.
- **Pros:** Window-targeted — captures correctly even when occluded by other windows. Modern API (Win10 1903+). Same `dxcam` library as Option A — switching backend is a single parameter change: `dxcam.create(backend='dxgi')` vs `dxcam.create(backend='winrt')`.
- **Cons:** Cannot capture minimized windows (documented WGC limitation). Shows a yellow capture border (suppressible on Win11). WGC backend in dxcam is newer/less battle-tested than DXGI.
- **Overhead:** ~0 CPU idle, ~5ms per grab, GPU-composited.

#### Option C: Win32 PrintWindow + PW_RENDERFULLCONTENT via ctypes
- **How:** `ctypes.windll.user32.PrintWindow(hwnd, hdc, 0x00000002)`. Zero new dependencies. `PW_RENDERFULLCONTENT` (Windows 8.1+) instructs DWM to composite the window's backing texture into the DC, capturing DirectX and OpenGL content correctly. This is the standard approach used by most game automation bots.
- **Pros:** Works when window is behind other windows (occluded) — DWM backing texture is always current. Works for OpenGL/DirectX via DWM flush. Zero new dependencies (ctypes only). ~5-20ms per capture.
- **Cons:** Cannot capture minimized windows (DWM suspends compositing). Triggers a DWM flush per capture (slightly heavier than DXGI). `PW_RENDERFULLCONTENT` (0x00000002) is undocumented and not in `win32con` constants.
- **Verdict: VIABLE AS FALLBACK** — Excellent zero-cost addition to the fallback chain. Handles occlusion (which DXcam DXGI cannot) with no new dependencies. Slower than DXcam but well within our 1-2fps budget. Base `PrintWindow` without the flag is still broken for GPU content.
- **Note:** Workaround for minimized windows: use `SetWindowPos` to move off-screen (negative coordinates) instead of minimizing. This keeps DWM compositing active while keeping the window invisible to the user.

#### Option D (not viable): Continuous scrcpy H.264 decode
- Rejected as primary because it's continuous (uses GPU for encoding), and we need on-demand capture.
- Still used for operator visibility and debug recording per substrate plan.

### Recommended: Option A (DXcam DXGI) as primary host shim, Option B (WGC) as one-line upgrade

**Why A over B:** DXcam's DXGI backend is battle-tested and fastest. For our use case (emulator visible on screen), DXGI region capture is simpler and more reliable than WGC window targeting. The emulator is typically full-screen or prominently placed — occlusion is rare.

**Why not B alone:** WGC is available as a one-line upgrade — `dxcam.create(backend='winrt')` instead of `dxcam.create(backend='dxgi')`. Same library, same API. If occlusion becomes a problem, flip the backend flag. Adding `[winrt]` extras is ~5MB additional.

**Why ctypes, not pywin32:** ALAS itself uses `ctypes.windll.user32` for all Windows API calls (see `vendor/.../platform/platform_windows.py`). pywin32 is a 30MB wheel for functionality that `ctypes` provides with zero additional dependencies. We follow the ALAS precedent here.

**Why not adopt ALAS wholesale:**

| Factor | ALAS | Our needs |
|---|---|---|
| Python version | 3.7 (pinned) | >=3.11 |
| adbutils | 0.11.0 (2021) | >=0.11.0 (latest API-compatible) |
| opencv | 4.5.3 (2021) | >=4.10.0 |
| numpy | 1.16.6 (ancient) | >=1.26.0 |
| scrcpy-server | v1.20 (2021) | v3.x (2025) |
| License | GPL-3.0 | We are MIT |
| Host-side capture | None | Required |
| Config coupling | Deep (ALAS config system) | Thin (our TransportConfig) |
| Class hierarchy | 7-level multiple inheritance | Not needed |

**What to lift from ALAS:**
1. Method dictionary pattern (`screenshot_methods = {"name": self.method}`)
2. Error-specific retry with recovery actions (reconnect vs reinstall vs restart)
3. `check_screen_black()` concept (but improved: histogram analysis, not just `sum < 1`)
4. Rate limiting (`Timer` for min interval between captures)

**What NOT to lift:**
1. The inheritance hierarchy (Screenshot inherits from 7 method classes)
2. The config system coupling
3. Ancient dependency versions
4. The `_screen_black_checked = True` pattern (check-once-then-never-again is wrong)

### Invalidation Rationale for Alternatives

- **Option C (PrintWindow):** Fundamentally broken for OpenGL/DirectX emulator windows — returns black or stale GDI content. Same class of bug as ADB screencap.
- **Option D (continuous scrcpy):** Wrong resource model — we need on-demand, not streaming. Already correctly scoped as debug-only in substrate plan.
- **Adopting ALAS wholesale:** GPL incompatibility with our MIT license. Python 3.7 deps would regress our stack. ALAS has no host-side capture (the entire point). The useful patterns are ~200 lines of code to re-implement cleanly.

## Implementation Plan

### Phase 1: Frame Validation (capture.py hardening)

**Goal:** No black frame ever reaches the VLM pipeline.

**Changes to `state_cartographer/transport/capture.py`:**

1. Add `validate_frame(data: bytes) -> FrameVerdict` — decode PNG, check dimensions (1280x720), compute mean pixel value, reject if mean < 1.0 or dimensions wrong. Note: `mean < 1.0` on a [0,255] scale means effectively all-zeros (pure black). This is near-zero detection, not "dim screen" detection — legitimate dark game scenes (loading screens, night battles) will have mean values well above 1.0. This matches ALAS's approach (`sum(color) < 1` across RGB).
2. Add `FrameVerdict` dataclass: `valid: bool, width: int, height: int, mean_brightness: float, byte_count: int, rejection_reason: str | None`.
3. Modify `screenshot_png()` to call `validate_frame()` and retry up to 3 times on failure.
4. Add structured logging: every capture logs `{method, bytes, mean_brightness, valid, latency_ms}`.

**New dependency:** `Pillow` (already in `[vision]` optional deps).

**adbutils 2.x upgrade note:** `adbutils` 2.x provides a built-in `d.screenshot()` returning a PIL image directly, which eliminates manual `shell(["screencap", "-p"])` decode. Consider upgrading `adb.py:screenshot_png()` to use `self.device.screenshot()` as part of this phase. The core `AdbClient`/`AdbDevice`/`.shell()` API is stable across 0.11→2.x; only `current_app()` and `package_info()` were removed (neither is used in our transport layer).

**Estimated size:** ~80 lines added to capture.py.

### Phase 2: Host-Side Capture Shim (new file)

**Gate:** Phase 2 proceeds after Phase 1 is deployed. If Phase 1 telemetry shows ADB black frame rate >5% of captures, the host shim is justified. If <1%, defer. Between 1-5%, user discretion.

**New file:** `state_cartographer/transport/host_capture.py`

**Contents:**
1. `HostCapture` class:
   - `__init__(window_title: str = "MEmu", min_size: tuple[int, int] = (640, 480))` — configures window search criteria
   - `find_window() -> int | None` — uses `ctypes.windll.user32.EnumWindows` to scan all windows matching `window_title`, then filters by minimum size (`min_size`) to find the actual viewport window (not the 30+ small helper/child windows MEmu creates). Optionally filters by window class name (e.g., `Qt5QWindowIcon` for MEmu).
   - `get_window_rect() -> tuple[int, int, int, int]` — bounding box via `ctypes.windll.user32.GetWindowRect()`, clamped to monitor bounds to handle partially off-screen windows
   - `is_window_visible() -> bool` — `ctypes.windll.user32.IsWindowVisible()` AND NOT `ctypes.windll.user32.IsIconic()` (minimized)
   - `window_state() -> WindowState` — returns `VISIBLE | MINIMIZED | HIDDEN` enum
   - `grab_frame() -> np.ndarray | None` — DXcam region capture of window rect with `processor_backend='numpy'`
   - `grab_frame_png() -> bytes | None` — same but encoded as PNG via Pillow
2. Lazy DXcam initialization — camera created on first call via `dxcam.create(processor_backend='numpy')`, released on `close()`.
3. All Win32 calls use `ctypes.windll.user32` — zero pywin32 dependency.
4. Region coordinate clamping — `grab_frame()` clamps the window rect to `(0, 0, monitor_width, monitor_height)` to prevent DXGI errors when the window extends beyond monitor bounds.
5. Lazy `dxcam` import — `try: import dxcam except ImportError: dxcam = None`. When `dxcam` is not installed (optional dep), `HostCapture` methods return `None` and the fallback chain skips host capture gracefully.

**Known MEmu window discovery issue:** MEmu creates 30+ windows all titled "MEmu" with sizes ranging from 78x74 to 2560x1440. The viewport is the largest window. `find_window()` uses `EnumWindows` + size filtering (minimum 640x480) to find the correct one. This approach generalizes to LDPlayer and BlueStacks which also have multiple windows per instance.

**New dependency:** `dxcam` (add to `[piloting]` optional deps). No pywin32 needed — `ctypes` suffices.

**Estimated size:** ~150 lines.

### Phase 3: Multi-Method Capture with Fallback Chain

**Modify:** `state_cartographer/transport/capture.py`

**Architecture (lifted from ALAS pattern):**

```python
class Capture:
    def __init__(self, adb: Adb, config: TransportConfig):
        self._methods = {
            "adb_screencap": self._capture_adb,
            "host_dxcam": self._capture_host,
            "host_printwindow": self._capture_printwindow,
        }
        self._fallback_order = ["adb_screencap", "host_dxcam", "host_printwindow"]
        self._active_method = "adb_screencap"

    def screenshot(self) -> CaptureResult:
        """Capture with validation and fallback."""
        for method_name in self._method_order():
            frame = self._methods[method_name]()
            verdict = validate_frame(frame)
            if verdict.valid:
                return CaptureResult(data=frame, method=method_name, verdict=verdict)
            log.warning(f"{method_name} failed validation: {verdict.rejection_reason}")
        raise CaptureError("All capture methods failed validation")
```

**Fallback behavior:**
- Try active method first (default: adb_screencap)
- If validation fails, try next method in fallback chain
- If host_dxcam is tried and window not visible, skip it (log reason)
- Track success rate per method — if a method fails 3x consecutively, demote it in the order

**Retry architecture (two levels):**
- **Inner retry** (Phase 1): Each method retries up to 3 times internally before reporting failure. This handles transient issues (ADB timeout, framebuffer not flushed yet).
- **Outer fallback** (Phase 3): If a method's inner retry exhausts, the fallback chain tries the next method. This handles systematic failures (ADB consistently returning black on this emulator).

**Estimated size:** ~60 lines refactor of existing capture.py.

### Phase 4: CaptureResult and Structured Telemetry

**New model:** Add `CaptureResult` to `models.py`:

```python
@dataclass
class CaptureResult:
    data: bytes
    method: str
    verdict: FrameVerdict
    latency_ms: float
    timestamp: float
    fallback_used: bool
```

**Telemetry:** Each capture logs an NDJSON event to `data/events/memu-transport/captures.ndjson`:
```json
{"ts": 1711234567.89, "method": "adb_screencap", "valid": true, "mean_brightness": 142.3, "bytes": 1048576, "latency_ms": 112, "fallback_used": false}
```

This gives us data to understand capture reliability over time.

### Phase 5: Integration and Config

**Update `configs/memu.json`:**
```json
{
  "fallback_observation": "adb_screencap",
  "host_capture_window_title": "MEmu",
  "capture_fallback_chain": ["adb_screencap", "host_dxcam"],
  "capture_validation_min_brightness": 1.0
}
```

**Update `__init__.py`:** Export `HostCapture`, `CaptureResult`, `FrameVerdict`.

**Update `pyproject.toml`:** Add `dxcam` to `[piloting]` deps. No pywin32 needed — ctypes handles Win32 calls.

**Update `config.py`:** Add `host_capture_window_title: str`, `capture_fallback_chain: list[str]`, and `capture_validation_min_brightness: float` fields to `TransportConfig` dataclass. Update `load_config()` to parse these from `configs/memu.json`.

**Existing functions:** `capture_burst()` and `Capture.save_screenshot()` are preserved. `capture_burst()` gains validation (each frame in the burst is validated). `save_screenshot()` delegates to the new `screenshot()` method.

## The Three Window States — Honest Assessment

| State | ADB screencap | Host DXcam (DXGI) | Host WGC | PrintWindow+PW_RENDERFULLCONTENT |
|---|---|---|---|---|
| Visible on screen | Works (but black frame risk) | Works perfectly | Works perfectly | Works (via DWM flush) |
| Occluded (behind windows) | Works (but black frame risk) | FAILS — captures occluder | Works perfectly | Works (DWM backing texture) |
| Minimized | Works (but black frame risk) | FAILS — not on monitor | FAILS — WGC limitation | FAILS — DWM suspends compositing |
| Hidden (SW_HIDE) | Works (but black frame risk) | FAILS — not on monitor | FAILS — no window | FAILS — no window |

**Key insight:** ADB screencap is actually the ONLY method that has a chance of working when the emulator is minimized — because it reads the Android-side framebuffer which may still be valid. The host-side shim is a BACKUP for when ADB fails while the window IS visible, not a replacement for all states.

**Recommended operating posture:** Keep the emulator visible on a secondary monitor or a dedicated virtual desktop. This maximizes capture reliability across both Android-side and host-side methods.

## Dependencies Added

| Package | Purpose | Size | Why |
|---|---|---|---|
| `dxcam` | DXGI/WGC host capture | ~2MB | Core of the host shim. Use `processor_backend='numpy'` to avoid cv2 requirement. |
| `Pillow` | PNG decode for validation | Already in [vision] | Frame validation |
| `numpy` | Pixel array analysis | Already in [piloting] | Mean brightness |

Total new: `dxcam` (~2MB). Window discovery uses `ctypes.windll.user32` (stdlib) — no pywin32 needed.

Optional upgrade: `pip install "dxcam[winrt]"` (~5MB additional) to enable WGC backend for occlusion-proof capture.

## Success Criteria

1. No black frame (mean brightness < 1.0) ever reaches the VLM pipeline
2. When emulator is visible and ADB returns black, host capture produces a valid frame
3. Capture telemetry NDJSON records every capture with method/validity/latency
4. `capture.py` stays under 250 lines total
5. Host capture shim under 150 lines
6. All new code has zero ALAS dependencies — patterns lifted, not code copied
7. Tests: `test_validate_frame_rejects_black`, `test_fallback_chain_uses_host_on_black`, `test_host_capture_finds_window`

## File Changes Summary

| File | Action | Lines |
|---|---|---|
| `state_cartographer/transport/capture.py` | Modify — add validation + fallback chain | ~140 lines (was 58) |
| `state_cartographer/transport/host_capture.py` | New — DXcam host capture shim + ctypes window discovery | ~150 lines |
| `state_cartographer/transport/models.py` | Modify — add FrameVerdict, CaptureResult | ~30 lines |
| `state_cartographer/transport/__init__.py` | Modify — export new types | ~5 lines |
| `pyproject.toml` | Modify — add dxcam to [piloting] | ~2 lines |
| `configs/memu.json` | Modify — add host capture config | ~4 lines |
| `tests/test_capture_validation.py` | New — frame validation tests | ~60 lines |

## ADR: Host-Side Capture Shim

- **Decision:** Add DXcam-based host-side window capture as fallback for ADB screencap failures.
- **Drivers:** ADB screencap returns black on MEmu OpenGL. All Android-side methods read the same broken framebuffer. Host-side capture reads from a fundamentally different data source (GPU desktop output).
- **Alternatives considered:** (A) DXcam/DXGI region capture, (B) WGC window capture, (C) PrintWindow/BitBlt, (D) continuous scrcpy decode, (E) adopt ALAS pipeline wholesale.
- **Why chosen:** A+B via dxcam dual backend. Fastest, lightest, same library for both approaches. PrintWindow broken for OpenGL. scrcpy wrong resource model. ALAS has no host capture and GPL-incompatible.
- **Consequences:** Emulator must be visible on screen for host fallback to work. Minimized/hidden windows cannot use host capture — ADB is the only option in those states. DXcam is Windows-only — acceptable since this is a Windows-only project.
- **Follow-ups:** Monitor capture telemetry to measure ADB vs host success rates. Consider WGC backend if occlusion becomes a problem. Consider nemu_ipc shared-memory path for MEmu-specific optimization.
