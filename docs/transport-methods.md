# Transport Methods Reference

Single source of truth for all capture and input methods. Updated as we learn.

## Screen Capture Methods

| Method | How It Works | Status | Notes |
|--------|-------------|--------|-------|
| **ADB screencap** | Reads `/dev/graphics/fb0` framebuffer | ❌ BROKEN on MEmu OpenGL | Returns 0 bytes when GPU emulation enabled |
| **MaaFramework screenshot** | Uses MAA's internal capture path (not framebuffer) | ✅ WORKS | 100-140ms per capture, proven 2026-03-25 |
| **DroidCast** | SurfaceFlinger API via HTTP server APK | ⚠️ UNTESTED | APK exists in vendor, needs integration |
| **DroidCast_raw** | Raw RGB565 via HTTP | ⚠️ UNTESTED | Same as above but raw bitmap |
| **scrcpy stream** | MediaCodec encoder via video stream | ⚠️ UNTESTED | Need to decode H.264 frame |
| **aScreenCap** | Custom binary with LZ4 compression | ⚠️ UNTESTED | Binary exists in vendor/bin/ascreencap/ |
| **nemu_ipc** | MEmu shared memory via DLL | ⚠️ UNTESTED | MEmu-specific, MuMu12 only |
| **ldopengl** | LDPlayer OpenGL capture | ❌ REJECTED | LDPlayer-specific |
| **Win32 PrintWindow** | Host-side window capture | ⚠️ UNTESTED | Last resort fallback |

### Research Findings (2026-03-25)

**Why ADB screencap fails on MEmu OpenGL:**
- MEmu with `-gpu on` (OpenGL) bypasses the framebuffer
- Rendering goes directly to GPU, framebuffer contains stale/empty data
- Docs state: "When GPU emulation is enabled, the framebuffer will typically only be used during boot"
- Sometimes works (race condition with double buffering) — explains mixed results

**Why MaaFramework works:**
- Uses different capture path than direct framebuffer read
- Not affected by OpenGL framebuffer bypass

## Input/Touch Methods

| Method | How It Works | Status | Notes |
|--------|-------------|--------|-------|
| **ADB input** | `adb shell input tap/swipe` | ✅ WORKS | Basic, slow (~100ms latency) |
| **MaaTouch** | Precision touch protocol via socket | ✅ WORKS | Fast, low latency, needs binary deployed |
| **minitouch** | minitouch protocol | ⚠️ UNTESTED | Similar to MaaTouch |
| **Hermit** | Hermit framework | ❌ REJECTED | Different emulator |
| **uiautomator2** | UI Automator 2 | ❌ BROKEN | Doesn't work on Unity games |

### MaaTouch Notes

- Binary: `vendor/AzurLaneAutoScript/bin/MaaTouch/`
- Needs deployment to `/data/local/tmp/maatouchsync` on device
- Used by ALAS and StarRailCopilot for precision input
- Low latency compared to ADB input

## Method Selection Logic

```
1. Try MaaFramework screenshot (primary capture)
2. If fails → try ADB screencap
3. If fails → try DroidCast
4. If fails → try scrcpy stream
5. If fails → Win32 PrintWindow (last resort)

Input always: MaaTouch > ADB input fallback
```

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

- ✅ ADB shell commands work
- ✅ MaaAdapter screenshot works (100-140ms)
- ✅ tap, swipe, key, text via ADB
- ✅ scrcpy attaches for debug viewing
- ✅ Reconnection works

## See Also

- Pipeline plan: `docs/plans/memu-transport-pipeline.md`
- Substrate decision: `docs/plans/substrate-and-implementation-plan.md`
- Probe results: `docs/memory/2026-03-25-memu-transport-probe-results.md`
