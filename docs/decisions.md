# Decision Log

## 2026-03-26: Pull architecture for screenshot consumption

**Decision:** Consumers pull screenshots synchronously via `adb.screenshot_png()` when they need one. No background capture thread, no ring buffer, no push pipeline.

**Context:**

The FrameRing design proposed a push architecture: a background thread continuously captures frames into a ring buffer, and consumers sample from it. This was motivated by two concerns:

1. **Black frame resilience** — keep capturing so the ring always has a recent good frame even if some captures fail
2. **Decoupled latency** — VLM calls (1-5s) shouldn't block capture

Both concerns evaporated:

- Vulkan rendering makes ADB screencap 100% reliable. There are no bad frames to skip over.
- At ~132ms per ADB round-trip, a synchronous pull adds trivial latency compared to a VLM call (1-5s). The consumer is already waiting seconds for the model — 132ms more doesn't matter.

**Pull vs push tradeoffs:**

| | Pull (chosen) | Push (deferred) |
|---|---|---|
| **Complexity** | Zero — call a function, get bytes | Thread lifecycle, ring buffer, synchronization, shutdown |
| **Latency** | 132ms per call | ~0.5ms (read from buffer) |
| **When latency matters** | When VLM calls are sub-10ms (not today) | When capture is unreliable and you need history |
| **Memory** | Zero — one frame at a time | 26MB+ pre-allocated ring |
| **Failure mode** | If ADB fails, caller sees it immediately | If ADB fails, ring serves stale frames silently |
| **Debuggability** | Stack trace points to the call site | Frame was captured N ms ago by a background thread |

**When to revisit:**

Push becomes worthwhile when:
- Capture starts failing again (new renderer, emulator update) and the ring's staleness buffer provides resilience
- Multiple consumers need frames simultaneously at different rates (VLM classifier + anomaly detector + state machine)
- Capture latency becomes the bottleneck (e.g., sub-100ms action loops where 132ms ADB round-trip matters)

None of these are true today. The FrameRing design (`docs/RES-research/RES-frame-ring-design.md`) is shelf-ready if they become true.

**Implications for the runtime:**
- The Pilot facade's `screenshot()` method is the entry point — it calls `adb.screenshot_png()` directly
- VLM classification will be: `screenshot → decode → send to model → get label`. Simple function call chain.
- No capture thread to manage, no ring to initialize, no shutdown to coordinate
- If the runtime later needs continuous observation, it can add a capture loop then — but that loop will be in the runtime layer, not the transport layer

---

## 2026-03-26: Defer capture engineering — Vulkan eliminated the need

**Decision:** Defer FrameRing, ring buffer, capture thread, and all further capture-side engineering until real problems arise. Use synchronous `adb.screenshot_png()` directly.

**Context:**
- FrameRing (ring buffer + background capture thread) was designed to handle black frames, capture failures, and decoupled VLM consumption
- Vulkan rendering eliminated the failure mode entirely: 316/316 frames, 0 failures, 0 black frames
- Synchronous ADB screencap at ~7.6 FPS is fast enough — game state transitions take 200-500ms
- The FrameRing design is valid research but solves a problem that no longer exists
- Building it now would be over-engineering against a hypothetical

**What is deferred:**
- FrameRing implementation (`state_cartographer/transport/frame_ring.py`)
- Background capture thread
- Half-res BGRA ring buffer
- Anomaly pre-roll deque
- Host-side capture shim (DXcam/PrintWindow)
- MaaFramework as capture fallback

**What remains ready if needed:**
- Design doc: `docs/RES-research/RES-frame-ring-design.md` (benchmarks, API, architecture all documented)
- Stress test: `scripts/stress_test_adb.py` (can re-validate at any time)

**Trigger to revisit:** If ADB screencap starts failing again (renderer change, emulator update, new device), revisit FrameRing. The design is shelf-ready.

---

## 2026-03-25: Vulkan rendering mode is the substrate answer

**Decision:** Switch MEmu to Vulkan rendering. ADB screencap becomes the primary (and likely only) capture method needed.

**Context:**
- ADB screencap returns 0 bytes on OpenGL — the original blocker for this entire project
- Switching MEmu to DirectX: Azur Lane won't launch (stuck at 59%, GLES→DX translation breaks Unity shaders)
- Switching MEmu to Vulkan: game runs perfectly, ADB screencap returns valid frames 100% of the time

**Evidence:**
- Stress test: 316 frames (50 burst + 266 timed over 2 minutes), zero failures, zero black frames, zero corruption
- Frame sizes: 493KB–1529KB (real game content, not black/white/empty)
- Data (local-only, not committed; see summary above): `data/stress_test/vulkan_run1/report_20260325_223419.json`

**Impact:**
- MaaFramework demoted from "primary capture" to "optional fallback"
- Multi-method CaptureManager with 5-method fallback chain → simplified to ADB screencap primary
- ALAS device module steal plan → cancelled (was only needed because screencap was broken)
- Host-side capture shim (DXcam/PrintWindow) → deferred indefinitely
- The entire transport layer simplifies dramatically

**Operational requirement:** MEmu MUST be configured with Vulkan rendering mode. Add to setup docs.

---

## 2026-03-25: Do NOT fork StarRailCopilot

**Decision:** Do not fork StarRailCopilot at this time.

**Context:**
- Considered forking StarRailCopilot (LmeSzinc's "next gen ALAS") to get working device/transport layer
- StarRailCopilot has 4.1k stars, 2,065 commits, same device module as ALAS
- Same fundamental problem: black screenshots on MEmu OpenGL via ADB screencap
- StarRailCopilot is template-matching-based, would need to replace detection layer anyway
- Forking adds a large, unfamiliar codebase with its own conventions and debt

**Alternatives considered:**
1. Fork StarRailCopilot → rejected (too much surface area, same black screenshot problem)
2. Fork ALAS directly → rejected (50+ modules, 296 Python files, deeply coupled)
3. Import ALAS as library → rejected (runtime dependency on ALAS execution)
4. Port ALAS device module standalone → rejected (164 import dependencies, tightly coupled monolith)

**Status:** Moot — Vulkan rendering solved the underlying screencap problem.

---

## Prior Decisions

*(Add prior decisions here as they occur)*
