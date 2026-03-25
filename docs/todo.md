# Todo

Thin tracker. Current truth only.

## Now

- Branch: `transport/memu-substrate-slice`
- **ADB screencap is BROKEN on MEmu OpenGL** — returns 0 bytes (confirmed 2026-03-25)
- `adbutils` works for shell commands but screencap returns empty
- Need to test alternative capture methods: DroidCast, scrcpy stream, nemu_ipc

## Next

1. **Step 1:** ~~Replace subprocess ADB with adbutils~~ ✅ DONE
2. **Step 2:** ~~Add MaaTouch support~~ ✅ DONE  
3. **Step 3:** ~~Add screenshot methods~~ ❌ BROKEN — ADB screencap returns 0 bytes on MEmu
4. **Step 4:** ~~Run `pip install -e .` to install adbutils~~ ✅ DONE
5. **Step 5:** Test DroidCast APK as alternative capture method
6. **Step 6:** Test scrcpy stream as alternative capture method
7. **Step 7:** Write and run live integration tests against MEmu
8. **Step 8:** Build Tier 2 VLM grounding loop (observe-act-observe on real device)

## Blockers

- **CRITICAL:** ADB screencap returns 0 bytes — capture is completely broken
- MaaTouch binary needs to be deployed to MEmu device (`/data/local/tmp/maatouchsync`)

## Deferred

- MaaFramework / MaaMCP (requires full MAA Windows DLL installation)
- Host-side capture shim (DXcam / PrintWindow) — NOW RELEVANT AGAIN, ADB screencap is broken
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works
- Replay and teacher layers
- Forking StarRailCopilot — rejected (see docs/decisions.md)

## See Also

- stress test results: data/stress_test/
- substrate decision and implementation plan: [substrate-and-implementation-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/substrate-and-implementation-plan.md)
- runtime architecture (tiered): [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- runtime overview: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- testing plan: [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md)
- workflow inventory: [azur-lane-workflows.md](/mnt/d/_projects/MasterStateMachine/docs/workflows/azur-lane-workflows.md)
- decisions log: [decisions.md](/mnt/d/_projects/MasterStateMachine/docs/decisions.md)
