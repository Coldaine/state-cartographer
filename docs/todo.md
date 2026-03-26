# Todo

Thin tracker. Current truth only.

## Now

- **Transport layer is done.** Vulkan + ADB screencap is 100% reliable. MaaTouch handles input. Pilot facade unifies both.
- Capture engineering is deferred — synchronous `adb.screenshot_png()` is sufficient until proven otherwise (see `docs/decisions.md`, 2026-03-26)
- Next work is on the **runtime and VLM side** — what to do with the screenshots, not how to get them

## Next

1. ~~**Step 1:** Replace subprocess ADB with adbutils~~ ✅ DONE
2. ~~**Step 2:** Add MaaTouch support~~ ✅ DONE
3. ~~**Step 3:** Add screenshot methods~~ ✅ SOLVED — Vulkan + ADB screencap = 100% reliable
4. ~~**Step 4:** Run `pip install -e .` to install adbutils~~ ✅ DONE
5. ~~**Step 5:** Build FrameRing-backed observation layer~~ ⏸️ DEFERRED — Vulkan eliminated the failure mode this solved
6. **Step 5 (new):** Wire VLM page classification using synchronous capture (local llama-swap + KIMI spot-check)
7. **Step 6:** Build Tier 2 VLM grounding loop (observe-act-observe on real device)
8. **Step 7:** Clean up dead code paths that existed only to work around OpenGL capture failure

## Blockers

- None. Vulkan + ADB screencap is the substrate.

## Resolved

- ~~**CRITICAL:** ADB screencap returns 0 bytes~~ → **FIXED** by switching MEmu to Vulkan rendering
- ~~MaaFramework as primary capture~~ → **No longer needed**, demoted to fallback
- ~~Multi-method CaptureManager with fallback chain~~ → **Simplified**, ADB screencap is primary on Vulkan
- ~~ALAS device module steal~~ → **Rejected** (164 deps), and now unnecessary
- ~~StarRailCopilot fork~~ → **Rejected**, and now unnecessary

## Deferred

- FrameRing / ring buffer / capture thread — Vulkan eliminated the failure mode; design is shelf-ready in `docs/RES-research/RES-frame-ring-design.md`
- MaaFramework / MaaMCP — fallback only, not primary
- Host-side capture (DXcam/PrintWindow) — fallback only, not primary
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works

## See Also

- stress test results (local-only, not committed): `data/stress_test/vulkan_run1/`
- FPS analysis: [RES-adb-screencap-fps-analysis.md](RES-research/RES-adb-screencap-fps-analysis.md)
- frame ring design: [RES-frame-ring-design.md](RES-research/RES-frame-ring-design.md)
- pipeline plan: [memu-transport-pipeline.md](plans/memu-transport-pipeline.md) (capture order updated)
- decisions log: [decisions.md](decisions.md)
