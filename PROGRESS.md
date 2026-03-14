# Progress

## Current Focus

Push/PR recovery for Phase 2 ALAS ingestion.

## Verified Current State

- Current branch: `feature/phase2-alas-conversion`
- Branch is local only
- No open PR exists for the current branch
- Push currently fails in `.githooks/pre-push`
- Root cause: Ruff is linting `vendor/AzurLaneAutoScript` and failing on third-party code
- The highest-impact repo docs and hooks have now been aligned to `scripts/`, `screenshot_mock.py`, and `vendor/AzurLaneAutoScript/`

## What Is Actually Blocked

- Any branch that stages the ALAS submodule or vendor tree cannot push cleanly
- Planning is misleading because Phase 2 docs imply tooling that does not yet exist
- Contributors and agents are likely to run broken commands from stale docs

## Active Recovery Sequence

1. Verify the updated push gate and CI lint scope behave correctly
2. Finish any remaining lower-priority doc cleanup
3. Decide and document the ALAS reference strategy
4. Begin actual Phase 2 implementation work

## Recommended PR Breakdown

1. `chore`: fix pre-push / Ruff vendor exclusions
2. `docs`: align repo docs with actual structure
3. `infra`: land ALAS reference strategy
4. `feat`: implement real Phase 2 converter/integration work

## Notes For Next Session

- Do not assume push succeeded until `git push -u origin HEAD` exits cleanly
- Do not assume a PR exists until `gh pr status` shows one for the current branch
- Do not start converter work before the push gate is fixed
- Use `docs/phase2-recovery-plan.md` as the source of truth for the current cleanup sequence
