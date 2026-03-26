# Todo

Thin tracker. Current truth only.

## Now

- Branch: `next-steps`
- **VULKAN SOLVES EVERYTHING** — switching MEmu to Vulkan rendering makes ADB screencap 100% reliable
- Proven 2026-03-25: 316 frames, 0 failures, 0 black frames, 0 corruption
- ADB screencap on Vulkan: ~1MB/frame, ~7.6 FPS, rock solid
- OpenGL screencap was broken (0 bytes). DirectX won't launch Azur Lane. **Vulkan is the answer.**
- MaaFramework as primary capture is NO LONGER NEEDED — plain ADB screencap works
- Frame ring buffer designed and implemented: `state_cartographer/base/frame_ring.py`
- Stress test proven: `scripts/stress_test_adb.py`
- Research docs complete: `docs/RES-research/RES-adb-screencap-fps-analysis.md`, `RES-frame-ring-design.md`

## Next

1. ~~**Step 1:** Replace subprocess ADB with adbutils~~ ✅ DONE
2. ~~**Step 2:** Add MaaTouch support~~ ✅ DONE
3. ~~**Step 3:** Add screenshot methods~~ ✅ SOLVED — Vulkan + ADB screencap = 100% reliable
4. ~~**Step 4:** Run `pip install -e .` to install adbutils~~ ✅ DONE
5. **Step 5:** Build FrameRing-backed observation layer (ring buffer + capture thread)
6. **Step 6:** Wire VLM classification on top of FrameRing (local llama-swap + KIMI spot-check)
7. **Step 7:** Build Tier 2 VLM grounding loop (observe-act-observe on real device)
8. **Step 8:** Clean up dead code paths that existed only to work around OpenGL capture failure

## Blockers

- None. Vulkan + ADB screencap is the substrate.

## Resolved

- ~~**CRITICAL:** ADB screencap returns 0 bytes~~ → **FIXED** by switching MEmu to Vulkan rendering
- ~~MaaFramework as primary capture~~ → **No longer needed**, demoted to fallback
- ~~Multi-method CaptureManager with fallback chain~~ → **Simplified**, ADB screencap is primary on Vulkan
- ~~ALAS device module steal~~ → **Rejected** (164 deps), and now unnecessary
- ~~StarRailCopilot fork~~ → **Rejected**, and now unnecessary

## Deferred

- MaaFramework / MaaMCP — fallback only, not primary
- Host-side capture (DXcam/PrintWindow) — fallback only, not primary
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works

## See Also

- stress test results: `data/stress_test/vulkan_run1/`
- FPS analysis: [RES-adb-screencap-fps-analysis.md](RES-research/RES-adb-screencap-fps-analysis.md)
- frame ring design: [RES-frame-ring-design.md](RES-research/RES-frame-ring-design.md)
- pipeline plan: [memu-transport-pipeline.md](plans/memu-transport-pipeline.md) (capture order updated)
- decisions log: [decisions.md](decisions.md)
