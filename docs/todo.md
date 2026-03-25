# Todo

Thin tracker. Current truth only.

## Now

- Branch: `transport/memu-substrate-slice`
- `state_cartographer/transport/` is **empty** — all prior implementation deleted (commit ef52c12)
- Substrate decision made: adbutils + MaaTouch + ADB screencap
- Implementation plan: [substrate-and-implementation-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/substrate-and-implementation-plan.md)
- Active scripts: `scripts/corpus_cleanup.py`, `scripts/kimi_review.py`, `scripts/vlm_detector.py`
- No live runtime exists

## Next

1. **Step 1:** Replace subprocess ADB with adbutils in `state_cartographer/transport/adb.py`
2. **Step 2:** Add MaaTouch support in `state_cartographer/transport/maatouch.py`
3. **Step 3:** Add screenshot methods in `state_cartographer/transport/capture.py`
4. **Step 4:** Write and run live integration tests against MEmu
5. **Step 5:** Build Tier 2 VLM grounding loop (observe-act-observe on real device)
6. **Step 6:** Add multi-step workflow execution with stuck detection
7. **Step 7:** Structured NDJSON event logging

## Blockers

- MaaTouch binary needs to be deployed to MEmu device (`/data/local/tmp/maatouchsync`)
- `adbutils` needs to be added to `pyproject.toml` dependencies and installed

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
