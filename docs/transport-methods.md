# Transport Methods Reference

Single source of truth for all capture and input methods. Updated as we learn.

## Screen Capture Methods

| Method | How It Works | Status | Notes |
|--------|-------------|--------|-------|
| **ADB screencap** | Reads framebuffer via `screencap` binary | **PRIMARY** | 100% reliable on Vulkan. ~132ms/call, ~1MB/frame. Stress tested: 316 frames, 0 failures. |
| **MaaFramework screenshot** | Uses MAA's internal capture path (not framebuffer) | Fallback only | 100-140ms per capture. Demoted after Vulkan solved the screencap problem. |
| **DroidCast** | SurfaceFlinger API via HTTP server APK | Deferred | APK exists in vendor, needs integration |
| **DroidCast_raw** | Raw RGB565 via HTTP | Deferred | Same as above but raw bitmap |
| **scrcpy stream** | MediaCodec encoder via video stream | Deferred | Need to decode H.264 frame |
| **aScreenCap** | Custom binary with LZ4 compression | Deferred | Binary exists in vendor/bin/ascreencap/ |
| **nemu_ipc** | MEmu shared memory via DLL | Deferred | MEmu-specific, MuMu12 only |
| **Win32 PrintWindow** | Host-side window capture | Last resort | Deferred indefinitely unless telemetry justifies |

### Why Vulkan Matters

- **OpenGL:** ADB screencap returns 0 bytes — MEmu bypasses framebuffer when GPU emulation enabled
- **DirectX:** Azur Lane won't launch (stuck at 59%, GLES→DX translation breaks Unity shaders)
- **Vulkan:** Game runs perfectly, ADB screencap returns valid frames 100% of the time

See `docs/decisions.md` for the full decision record and evidence.

## Input/Touch Methods

| Method | How It Works | Status | Notes |
|--------|-------------|--------|-------|
| **ADB input** | `adb shell input tap/swipe` | Fallback | Basic, slow (~100ms latency) |
| **MaaTouch** | Precision touch protocol via socket | **PRIMARY** | Fast, low latency, needs binary deployed |
| **minitouch** | minitouch protocol | Deferred | Similar to MaaTouch |
| **Hermit** | Hermit framework | Rejected | Different emulator |
| **uiautomator2** | UI Automator 2 | Rejected | Doesn't work on Unity games |

### MaaTouch Notes

- Binary: `vendor/AzurLaneAutoScript/bin/MaaTouch/`
- Needs deployment to `/data/local/tmp/maatouchsync` on device
- Used by ALAS and StarRailCopilot for precision input
- Low latency compared to ADB input

## Method Selection Logic

```
Capture: ADB screencap (Vulkan) — single method, no fallback chain needed
Input:   MaaTouch > ADB input fallback
```

The 5-method CaptureManager fallback chain was designed for the OpenGL era when screencap was broken. Vulkan eliminates that problem. Fallback methods are retained in this doc for reference but are not part of the current architecture.

## Unknowns / Need Testing

| Item | What We Don't Know |
|------|-------------------|
| **DroidCast on MEmu** | Does the APK run on MEmu x86? Does SurfaceFlinger work? |
| **nemu_ipc** | Does the DLL exist on our MEmu? Which version? |
| **scrcpy capture** | Can we extract single H.264 frame without full stream? |
| **aScreenCap** | Does it work on MEmu when ADB screencap fails? |
| **Win32 PrintWindow** | Does it capture emulator window cleanly? |

## Proven Working (2026-03-25 Probe)

From `docs/memory/2026-03-25-memu-transport-probe-results.md`:

- ADB shell commands work
- tap, swipe, key, text via ADB
- scrcpy attaches for debug viewing
- Reconnection works
- ADB screencap on Vulkan: 316 frames, 0 failures, 0 black frames, 0 corruption

## See Also

- Vulkan decision: `docs/decisions.md`
- Probe results: `docs/memory/2026-03-25-memu-transport-probe-results.md`
- Backend design constraints: `docs/runtime/backend-lessons.md`
