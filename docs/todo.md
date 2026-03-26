# Todo

Thin tracker. Current truth only.

## Now

1. Run VLM corpus sweep — multi-pass labeling to build state vocabulary and transition table (see [vlm-corpus-sweep-plan.md](plans/vlm-corpus-sweep-plan.md))
2. Build Tier 2 VLM grounding loop (observe-act-observe on real device)

## Blockers

- None

## Deferred

- FrameRing / ring buffer / capture thread — Vulkan eliminated the failure mode
- Emulator daemon (auto-launch MEmu, admin elevation) — not needed until unattended ops
- MaaFramework / MaaMCP — fallback only, not primary
- Host-side capture (DXcam/PrintWindow) — fallback only, not primary
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works

## Done

- Transport layer: adbutils ADB, MaaTouch input, Pilot facade, Vulkan screencap (100% reliable)
- ADB screencap failure investigation — resolved by Vulkan rendering mode
- Dead code removal: scrcpy vendor, probe, worker, capture.py, artifacts.py, examples/
- Docs cleanup: removed 11 stale/speculative docs, consolidated references

## See Also

- decisions log: [decisions.md](decisions.md)
- corpus sweep plan: [vlm-corpus-sweep-plan.md](plans/vlm-corpus-sweep-plan.md)
- runtime plan: [multi-tier-runtime-implementation-plan-2026-03-24.md](plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
