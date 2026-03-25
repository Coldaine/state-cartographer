# Todo

Thin tracker only.

## Now

- transport slice implementation on branch `transport/memu-substrate-slice`
- `state_cartographer/transport/` package: bootstrap, discovery, MaaAdapter (maafw + adb fallback), scrcpy probe, health/recovery
- `scripts/memu_transport.py` CLI: bootstrap, doctor, connect, capture, input, probe
- chosen control posture: `MaaMCP` + `scrcpy`, with `adbfriend` separate
- trusted active scripts: `scripts/corpus_cleanup.py`, `scripts/kimi_review.py`, `scripts/vlm_detector.py`, `scripts/memu_transport.py`
- 15 pure-code tests passing (`tests/transport/test_transport.py`)

## Next

1. Run live probes (`bootstrap`, `doctor`, `probe maa`, `probe scrcpy`) on the pinned MEmu instance.
2. Confirm scrcpy runtime-consumable vs debug-only verdict.
3. Rebuild only the thin runtime brain on top.

## Blockers

- live probe runs not yet executed against hardware
- no confirmed answer yet on `scrcpy` as runtime frame source

## Deferred

- replay and teacher layers
- maafw agent_path / MaaAgentBinary configuration

## See Also

- runtime architecture: [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- tool requirements: [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- tool setup and compatibility spike: [borrowed-control-tool-setup.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/borrowed-control-tool-setup.md)
- runtime scope: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- ALAS artifact guidance: [alas-artifacts.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-artifacts.md)
- corpus review procedure: [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
