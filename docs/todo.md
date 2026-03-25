# Todo

Thin tracker. Current truth only.

## Now

- Branch: `transport/memu-substrate-slice`
- **ADB screencap is BROKEN on MEmu OpenGL** — returns 0 bytes (confirmed 2026-03-25)
- `adbutils` works for shell commands but screencap returns empty
- Need to test alternative capture methods: DroidCast, scrcpy stream, Win32 PrintWindow
- Created comprehensive pipeline plan: `docs/plans/memu-transport-pipeline.md`
- Pipeline uses **immediate retries** (no artificial delay — ADB RT ~100ms is delay enough)

## Next

1. **Step 1:** ~~Replace subprocess ADB with adbutils~~ ✅ DONE
2. **Step 2:** ~~Add MaaTouch support~~ ✅ DONE  
3. **Step 3:** ~~Add screenshot methods~~ ❌ BROKEN — ADB screencap returns 0 bytes on MEmu
4. **Step 4:** ~~Run `pip install -e .` to install adbutils~~ ✅ DONE
5. **Step 5:** Build EmulatorDaemon to monitor/launch MEmu
6. **Step 6:** Build HealthCheck layer (detect render mode, verify connectivity)
7. **Step 7:** Build CaptureManager with multi-method fallback (screencap → DroidCast → scrcpy → Win32)
8. **Step 8:** Write and run live integration tests against MEmu
9. **Step 9:** Build Tier 2 VLM grounding loop (observe-act-observe on real device)

## Blockers

- **CRITICAL:** ADB screencap returns 0 bytes — capture is completely broken
- EmulatorDaemon needs MEmuConsole path and admin elevation support

## Deferred

- MaaFramework / MaaMCP (requires full MAA Windows DLL installation)
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works
- Forking StarRailCopilot — rejected (see docs/decisions.md)

## See Also

- stress test results: data/stress_test/
- NEW pipeline plan: [memu-transport-pipeline.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-transport-pipeline.md)
- substrate decision and implementation plan: [substrate-and-implementation-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/substrate-and-implementation-plan.md)
- runtime architecture (tiered): [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- runtime overview: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- testing plan: [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md)
- workflow inventory: [azur-lane-workflows.md](/mnt/d/_projects/MasterStateMachine/docs/workflows/azur-lane-workflows.md)
- decisions log: [decisions.md](/mnt/d/_projects/MasterStateMachine/docs/decisions.md)
