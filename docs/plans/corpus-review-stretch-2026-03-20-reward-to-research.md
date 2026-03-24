# Corpus Review Stretch: 2026-03-20 Reward To Research

## Purpose

This document is the immediate execution plan for the next corpus-review stretch.

It is narrower than [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md):
- `current-plan.md` owns repo-wide tactical direction
- this file owns the next concrete stretch review only

## Selected Stretch

Use the next `raw_stream` window after the already-confirmed commission stretch:

- source: [data/raw_stream](/mnt/d/_projects/MasterStateMachine/data/raw_stream)
- frame window: `2026-03-20 00:23:40.062` to `2026-03-20 00:23:56.700`
- likely frame range:
  - [20260320_002340_062.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002340_062.png)
  - through `20260320_002356_700.png`
- corresponding log: [2026-03-20_PatrickCustom.txt](/mnt/d/_projects/MasterStateMachine/vendor/AzurLaneAutoScript/log/2026-03-20_PatrickCustom.txt)

Key nearby log anchors:

- `00:23:40.304` `[UI] page_reward`
- transition through `page_main`, `page_reshmenu`, and `page_research`
- `00:23:50.357` `QUEUE RECEIVE`
- `00:23:53.707` first `GET_ITEMS_1 appeared`

## Why This Stretch Is Next

This is the best next stretch because it is:

- immediately adjacent to the already-reviewed commission window
- dense with both screenshot and log coverage
- likely to expose a real transition chain rather than a single settled page
- useful for deciding whether reward, research, queue receive, and get-items are distinct visible states or only transient overlays

## Questions To Answer

The review should answer these exact questions:

1. What visible page sequence actually occurs over the stretch?
2. Where does the UI settle versus merely transition?
3. Is `GET_ITEMS_1` visually distinct enough to deserve its own state or modal label?
4. Are the intermediate steps better described as page changes, overlays, or action-result substate changes?
5. Would a future state machine need separate states here, or just a smaller number of higher-confidence transitions?

## Decision Rule

Use this rule during review:

- call it a `page` when the underlying navigation destination has clearly changed and settled
- call it an `overlay` when the underlying page is still visible but temporarily covered by a popup, reward layer, or item-claim surface
- call it a `transition` only when the UI is visibly changing and has not yet settled into either a page or an overlay

If two adjacent frames disagree, prefer the first frame where the new surface is visibly stable.

## Execution Plan

1. Pull the exact frame subset for the time window, plus 1 to 2 context frames before and after.
2. Pull the matching log slice covering the reward-to-research path and first item-claim event.
3. Inspect the images in order and note:
   - settled pages
   - transient overlays
   - first visible item-claim state
   - actual transition boundaries
4. Record one reviewed ledger row for the stretch.
5. Extract the state/substate candidates implied by the review.
6. Decide whether the next stretch should continue forward into the stuck/restart window or shift to a different ambiguity class.

## Expected Output

The stretch review should produce:

- one reviewed ledger entry
- a short visible timeline
- a list of candidate state/substate names
- a note on whether prior generated labels were wrong, too coarse, or unnecessary

Do not produce a new giant JSONL artifact for this step.

## Success Criteria

This stretch is successful if, after review, we can state clearly:

- what the visible sequence was
- which moments count as real state boundaries
- whether `queue receive` and `get items` are reusable state-machine concepts
- what should be reviewed next

## Fallback

If this stretch turns out to be too visually noisy or too sparse to be useful, use the next raw-stream failure window instead:

- `2026-03-20 00:24:10.732` to `00:25:00.895`

That fallback is the reward-claim failure and forced-restart sequence.
