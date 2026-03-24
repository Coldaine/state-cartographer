# Corpus Review Playbook

## Purpose

This document defines how to select and review small "golden" corpus stretches from screenshots plus nearby ALAS logs.

It answers a narrower question than [alas-build-plan.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-build-plan.md):
- `alas-build-plan.md` says what artifacts prework should produce
- this playbook says how to choose and review frame windows so those artifacts are worth trusting

See also:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [alas-build-plan.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-build-plan.md)

## Observed Timestamp Model

Observed from the retained corpus and code:

- `data/raw_stream/*.png` uses `YYYYMMDD_HHMMSS_mmm.png`
- ALAS logs use `YYYY-MM-DD HH:MM:SS.mmm`
- for same-day review windows, raw frame names and ALAS log lines can be compared directly by wall-clock time

Example:

- [20260320_002241_384.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002241_384.png) corresponds to `2026-03-20 00:22:41.384`
- [2026-03-20_PatrickCustom.txt](/mnt/d/_projects/MasterStateMachine/vendor/AzurLaneAutoScript/log/2026-03-20_PatrickCustom.txt) contains nearby lines at `00:22:42.xxx` through `00:23:06.xxx`

Important limits:

- frame cadence is sparse and irregular; there is not one screenshot per log event
- some later screenshot ranges do not have matching retained logs; do not pretend those are time-aligned review windows
- if a review crosses midnight, changes device timezone, or mixes runs, re-check alignment instead of assuming it

## What A Golden Stretch Is

A golden stretch is a short contiguous review window with:

- one screenshot sequence
- one nearby log slice
- one concise human-reviewed record of what is visibly true over time

Default size:

- `15` to `30` sequential frames before dedupe
- usually `8` to `20` representative frames after duplicate compression
- enough surrounding log lines to cover entry, transition, and settle

The goal is not to review everything. The goal is to build a small set of trusted windows that expose where logs are strong, where vision is strong, and where prior labels are wrong or too coarse.

## Stretch Selection Rules

Prefer stretches that contain at least one of these:

1. blocking modal or recovery event
2. stable page identity that is easy to verify visually
3. subtab discrimination such as `URGENT` vs `DAILY`
4. transition ambiguity where the log says `unknown` or the UI is mid-switch
5. action-result before/after evidence
6. long static plateaus where dedupe should dominate instead of frame-by-frame review
7. disagreement between prior machine labels and visible reality

Avoid as first-pass gold candidates:

- long black-frame runs unless the failure itself is the subject
- windows with no nearby log coverage
- isolated singleton frames when a short before/after window is available

## Cleanup Tooling

The active corpus-cleanup entrypoint is:

- [corpus_cleanup.py](/mnt/d/_projects/MasterStateMachine/scripts/corpus_cleanup.py)

It owns two subcommands:

- `dedupe`
- `black-frames`

Preferred commands:

```bash
uv run python scripts/corpus_cleanup.py dedupe \
  --input data/raw_stream \
  --output data/reports/raw-stream-dedupe.json
```

```bash
uv run --extra vision python scripts/corpus_cleanup.py black-frames \
  --json \
  --report data/reports/black-frame-dry-run.json
```

```bash
uv run --extra vision python scripts/corpus_cleanup.py black-frames \
  --delete \
  --json \
  --report data/reports/black-frame-delete.json
```

Black-frame verification rule:

1. file size is `<= 10000` bytes
2. grayscale mean is `<= 5.0`
3. grayscale standard deviation is `<= 2.0`

Keep the manifests. They are the durable record of what existed and what was removed.

## Cheap Review Tool

For cheap first-pass screenshot review, use:

- [kimi_review.py](/mnt/d/_projects/MasterStateMachine/scripts/kimi_review.py)

Use it for:

- visible text extraction
- visible region extraction
- closed-set provisional label selection
- disagreement surfacing before human review

Do not use it as accepted truth by itself.

## Pre-Review Hygiene

Before reviewing a stretch:

1. preserve the corpus state
   - keep black-frame manifests from [corpus_cleanup.py](/mnt/d/_projects/MasterStateMachine/scripts/corpus_cleanup.py) `black-frames`
   - keep duplicate-cluster reports from [corpus_cleanup.py](/mnt/d/_projects/MasterStateMachine/scripts/corpus_cleanup.py) `dedupe`
2. exclude obvious black-frame junk from candidate windows unless recovery behavior is the thing being studied
3. use duplicate reports to identify plateaus, but keep:
   - the first frame in the plateau
   - one representative middle frame
   - the last frame before change
4. pull the matching log slice before reviewing the images

The reports are part of the record of what existed. Do not delete or archive derived corpus artifacts until the provenance reports exist.

## Review Procedure

For each candidate stretch:

1. Define the window.
   - choose a start and end timestamp from the log
   - collect all sequential frames that fall inside or just around that window

2. Gather log anchors.
   - page switch or page arrive
   - click or action attempt
   - `unknown` / recovery / popup events
   - task boundary if one is visible in the log

3. Inspect the images in order.
   - first frame
   - representative middle frames
   - final settled frame
   - any frame near a disputed or `unknown` log span

4. Record what is visually true.
   - visible page
   - visible modal or blocking state
   - visible subtab, selection, or banner
   - transition point where the UI actually changes

5. Compare against prior machine hints.
   - any existing generated labels under `data/kimi_labels/`
   - note whether they are right, wrong, or too coarse

6. Produce one reviewed ledger row for the stretch.

## Minimum Information To Capture

Do not start with a rich JSON schema. Start with a minimal review ledger.

Useful fields:

- `stretch_id`
- `source`
- `log_file`
- `frame_start`
- `frame_end`
- `log_start`
- `log_end`
- `task_context`
- `visible_timeline`
- `transition_points`
- `machine_label_verdict`
- `confidence`
- `notes`

Recommended storage for the first pass:

- markdown table
- TSV
- or one short YAML block per stretch

The shape should stay easy to revise until repeated review proves which fields are actually stable and useful.

## Parallel Review Rule

Independent stretches can be reviewed in parallel by separate agents if they use the same ledger fields and do not overlap in frame ownership.

For parallel work:

- assign disjoint time windows
- keep one reviewer responsible for one stretch
- require the same evidence standard for every stretch
- merge only the reviewed ledger, not ad hoc narrative blobs

## First Confirmed Example

This window is already confirmed useful:

- log window: `2026-03-20 00:22:41.384` to `2026-03-20 00:23:07.204`
- frames:
  - [20260320_002241_384.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002241_384.png)
  - [20260320_002243_739.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002243_739.png)
  - [20260320_002253_364.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002253_364.png)
  - [20260320_002256_639.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002256_639.png)
  - [20260320_002259_542.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002259_542.png)
  - [20260320_002300_623.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002300_623.png)
  - [20260320_002302_889.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002302_889.png)
  - [20260320_002306_475.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002306_475.png)
  - [20260320_002307_204.png](/mnt/d/_projects/MasterStateMachine/data/raw_stream/20260320_002307_204.png)
- useful because it covers:
  - popup recovery
  - OS page identity
  - reward page identity
  - commission `URGENT` vs `DAILY`
  - transition periods where ALAS logs repeated `unknown`
- confirmed result:
  - nearby generated labels under `data/kimi_labels/` were partially wrong or too loose, so this is a real adjudication target rather than a redundant review window

## Current Seed Windows

The windows below are current review candidates.

Important scope note:

- the first confirmed example above was already image-reviewed directly
- the seed windows below are grounded in retained logs and file inventory, but they have not all been visually reviewed end-to-end yet

### Raw Stream Candidates

- `2026-03-20 00:23:40.062` to `00:23:56.700`
  - likely frames: `20260320_002340_062.png` through `20260320_002356_700.png`
  - useful because the log moves through `page_reward`, `page_main`, `page_reshmenu`, `page_research`, `QUEUE RECEIVE`, and first `GET_ITEMS_1`
  - ambiguity tested: detection lag versus a genuinely ambiguous navigation transition

- `2026-03-20 00:24:10.732` to `00:25:00.895`
  - likely frames: `20260320_002410_732.png` through `20260320_002500_895.png`
  - useful because this is the reward-claim failure window ending in `Wait too long`, `GameStuckError`, and forced restart
  - ambiguity tested: real item popup versus misread popup state versus hidden blocking overlay

- `2026-03-20 02:28:28.848` to `02:29:54.259`
  - likely frames: `20260320_022828_848.png` through `20260320_022954_259.png`
  - useful because it begins just after repeated pure-black screenshot warnings and continues through login and `GOTO_MAIN`
  - ambiguity tested: whether emulator recovery is visually stable before clicks resume

- `2026-03-20 02:31:51.138` to `02:32:37.076`
  - likely frames: `20260320_023151_138.png` through `20260320_023237_076.png`
  - useful because the log resolves a long `Unknown ui page` span into `page_exercise`, then moves into reward flow and ship acquisition
  - ambiguity tested: whether the source page is truly exercise and whether reward dismissal is visually distinct from ship-acquisition flow

- `2026-03-20 02:34:30.320` to `02:34:47.987`
  - likely frames: `20260320_023430_320.png` through `20260320_023447_987.png`
  - useful because it is the clearest commission-tab failure, with repeated `daily` / `urgent` / `unknown` switching and a warning that `Commission_switch` should be re-verified
  - ambiguity tested: bad tab asset versus unstable scroll region versus truly ambiguous tab state

### ALAS-Observe Candidates

- [20260314T210002Z-PatrickCustom-smoke](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke)
  - window: `2026-03-14T21:01:00.758Z` to `21:01:13.605Z`
  - screenshots: [000003.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000003.png), [000008.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000008.png), [000011.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000011.png), [000016.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000016.png), [000021.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000021.png), [000025.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000025.png), [000030.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000030.png), [000038.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210002Z-PatrickCustom-smoke/screenshots/000038.png)
  - useful because it is the cleanest stable guild baseline
  - ambiguity tested: locator failure on a normal guild screen despite `session.json` believing the page is already `page_guild`

- [20260314T210223Z-PatrickCustom-live](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210223Z-PatrickCustom-live)
  - window: roughly `2026-03-14T21:05:52.596Z` to `21:06:23.763Z`
  - screenshots: [000533.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210223Z-PatrickCustom-live/screenshots/000533.png), [000542.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210223Z-PatrickCustom-live/screenshots/000542.png), [000547.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210223Z-PatrickCustom-live/screenshots/000547.png), [000564.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210223Z-PatrickCustom-live/screenshots/000564.png)
  - useful because it is a short recovery sequence from guild into restart, login, and patch-note/announce UI
  - ambiguity tested: whether restart recovery is being semantically classified correctly instead of collapsed into generic `unknown`

- [20260314T210749Z-PatrickCustom-restart](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart)
  - window: roughly `2026-03-14T21:07:53.232Z` to `21:08:21.498Z`
  - screenshots: [000003.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000003.png), [000004.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000004.png), [000020.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000020.png), [000022.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000022.png), [000032.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000032.png), [000080.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000080.png), [000083.png](/mnt/d/_projects/MasterStateMachine/data/alas-observe/20260314T210749Z-PatrickCustom-restart/screenshots/000083.png)
  - useful because it tests whether navigation to guild succeeded while classification failed, with one black frame mixed in
  - ambiguity tested: navigation failure versus observation failure versus screenshot-provider glitch

## Practical Rule

If a stretch does not help answer one of these questions, it is probably not worth gold review yet:

- what page or substate is actually visible?
- what changed between frames?
- what did the log know correctly?
- what did the prior generated labels get wrong?
- what evidence would a future runtime actually need here?
