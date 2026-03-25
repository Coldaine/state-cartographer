# Todo

Thin tracker only.

## Now

- transport slice implementation on branch `transport/memu-substrate-slice`
- `state_cartographer/transport/` package: bootstrap, discovery, MaaAdapter (maafw + adb fallback), scrcpy probe, health/recovery
- `scripts/memu_transport.py` CLI: bootstrap, doctor, connect, capture, input, probe
- chosen control posture: `MaaMCP` + `scrcpy`, with `adbfriend` separate
- live probe results captured on 2026-03-25 against pinned MEmu serial `127.0.0.1:21503`
- accepted near-term runtime posture: Maa/ADB path for control plus `maamcp_screenshot` for observation
- trusted active scripts: `scripts/corpus_cleanup.py`, `scripts/kimi_review.py`, `scripts/vlm_detector.py`, `scripts/memu_transport.py`
- 15 pure-code tests passing (`tests/transport/test_transport.py`)

## Next

1. Strengthen post-action verification above the transport layer; keep raw frame diff as a cheap signal only.
2. Build the thin multi-step runtime loop on top of the proven Maa-first transport slice.
3. Persist structured step-by-step runtime events and screenshots before any semantic cache work.
4. Add live readiness/capture/recovery tests from `dev/testingADB.md`.

## Blockers

- `maafw` / native MaaFramework tooling is not installed locally, so the current posture remains degraded rather than preferred
- `scrcpy` is confirmed `debug_only` on this Windows MEmu setup; it is not a runtime frame source here

## Deferred

- replay and teacher layers
- maafw agent_path / MaaAgentBinary configuration

## See Also

- dated probe outcome: [2026-03-25-memu-transport-probe-results.md](/mnt/d/_projects/MasterStateMachine/docs/memory/2026-03-25-memu-transport-probe-results.md)
- runtime architecture: [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- substrate decision: [adb-touch-vision-substrate-selection-2026-03-25.md](/mnt/d/_projects/MasterStateMachine/docs/plans/adb-touch-vision-substrate-selection-2026-03-25.md)
- tool requirements: [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- tool setup and compatibility spike: [borrowed-control-tool-setup.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/borrowed-control-tool-setup.md)
- live ADB testing plan: [testingADB.md](/mnt/d/_projects/MasterStateMachine/docs/dev/testingADB.md)
- runtime scope: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- ALAS artifact guidance: [alas-artifacts.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-artifacts.md)
- corpus review procedure: [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
