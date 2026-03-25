# Todo

Thin tracker only.

## Now

- borrowed-substrate rebuild phase
- trusted active scripts: `scripts/corpus_cleanup.py`, `scripts/kimi_review.py`, `scripts/vlm_detector.py`
- chosen control posture: `MaaMCP` + `scrcpy`, with `adbfriend` separate

## Next

1. Prove `MaaMCP` on the pinned MEmu instance.
2. Prove whether `scrcpy` is runtime-consumable or debug-only on that setup.
3. Rebuild only the thin runtime brain on top.

## Blockers

- no confirmed `MaaMCP` + pinned MEmu baseline yet
- no confirmed answer yet on `scrcpy` as runtime frame source

## Deferred

- replay and teacher layers
- any repo-local transport ownership

## See Also

- runtime architecture: [multi-tier-runtime-implementation-plan-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/multi-tier-runtime-implementation-plan-2026-03-24.md)
- tool requirements: [agent-control-tool-requirements.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/agent-control-tool-requirements.md)
- tool setup and compatibility spike: [borrowed-control-tool-setup.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/borrowed-control-tool-setup.md)
- runtime scope: [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- ALAS artifact guidance: [alas-artifacts.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-artifacts.md)
- corpus review procedure: [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
