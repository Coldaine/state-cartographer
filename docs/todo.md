# Todo

Thin tracker. Current truth only.

## Now

- Branch: `transport/memu-substrate-slice`
- `state_cartographer/transport/` now has:
  - `adb.py` — **DONE**: adbutils-based, no subprocess
  - `maatouch.py` — **DONE**: precision touch protocol
  - `capture.py` — **DONE**: screenshot methods
  - `maamcp.py` — kept for reference but not used (MaaMCP deferred)
- `adbutils` added to `pyproject.toml`
- Substrate decision: adbutils + MaaTouch + ADB screencap

## Next

1. **Step 1:** ~~Replace subprocess ADB with adbutils~~ ✅ DONE
2. **Step 2:** ~~Add MaaTouch support~~ ✅ DONE
3. **Step 3:** ~~Add screenshot methods~~ ✅ DONE
4. **Step 4:** Run `pip install -e .` to install adbutils
5. **Step 5:** Write and run live integration tests against MEmu
6. **Step 6:** Build Tier 2 VLM grounding loop (observe-act-observe on real device)
7. **Step 7:** Add multi-step workflow execution with stuck detection
8. **Step 8:** Structured NDJSON event logging

## Blockers

- MaaTouch binary needs to be deployed to MEmu device (`/data/local/tmp/maatouchsync`)
- Need to verify `pip install -e .` installs adbutils correctly

## Deferred

- MaaFramework / MaaMCP (requires full MAA Windows DLL installation)
- Semantic embedding cache (Tier 1) — no data yet to justify it
- Teacher escalation (Tier 3) — not until Tier 2 baseline works
- Replay and teacher layers

## See Also

- substrate decision and implementation plan: [substrate-and-implementation-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/substrate-and-implementation-plan.md)
- runtime architecture (tiered): [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- probe evidence: [2026-03-25-memu-transport-probe-results.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-25-memu-transport-probe-results.md)
- runtime overview: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- testing plan: [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md)
- workflow inventory: [azur-lane-workflows.md](/mnt/d/_projects/MasterStateMachine/docs/workflows/azur-lane-workflows.md)
