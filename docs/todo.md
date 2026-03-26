# Todo

Thin tracker. Current truth only.

## Now

1. Wire VLM page classification using synchronous capture (local llama-swap + KIMI spot-check)
2. Build Tier 2 VLM grounding loop (observe-act-observe on real device)
3. Clean up dead code paths that existed only to work around OpenGL capture failure

## Blockers

- None

## Deferred

- FrameRing / ring buffer / capture thread — Vulkan eliminated the failure mode; design is shelf-ready in `docs/RES-research/RES-frame-ring-design.md`
- Emulator daemon (auto-launch MEmu, admin elevation) — not needed until unattended ops
- MaaFramework / MaaMCP — fallback only, not primary
- Host-side capture (DXcam/PrintWindow) — fallback only, not primary
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works

## Done

- Transport layer: adbutils ADB, MaaTouch input, Pilot facade, Vulkan screencap (100% reliable)
- MEmu transport pipeline plan — substantially complete (see `plans/memu-transport-pipeline.md`)
- ADB screencap failure investigation — resolved by Vulkan rendering mode
- Dead code removal: scrcpy vendor, probe, worker

## See Also

- decisions log: [decisions.md](decisions.md)
- stress test results (local-only): `data/stress_test/vulkan_run1/`
- FPS analysis: [RES-adb-screencap-fps-analysis.md](RES-research/RES-adb-screencap-fps-analysis.md)
- frame ring design: [RES-frame-ring-design.md](RES-research/RES-frame-ring-design.md)
- pipeline plan: [memu-transport-pipeline.md](plans/memu-transport-pipeline.md)
