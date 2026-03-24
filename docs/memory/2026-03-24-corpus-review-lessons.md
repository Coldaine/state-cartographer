# Corpus Review Lessons — 2026-03-24

## Purpose

Retain the most important lessons from the repo reset and the first direct screenshot-plus-log review pass.

See also:
- [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
- [reviewed_stretches.tsv](/mnt/d/_projects/MasterStateMachine/data/review/reviewed_stretches.tsv)
- [kimi_review.py](/mnt/d/_projects/MasterStateMachine/scripts/kimi_review.py)

## Tag Key

- `P0` = critical working rule
- `P1` = important operating rule
- `P2` = useful refinement

Topic tags are plain words such as `kimi`, `prompting`, `review`, `truth`, `logs`, `images`, `ontology`, and `artifacts`.

## Lessons

### 1. Generated label artifacts are not ground truth

Tags: `P0` `truth` `artifacts` `review`

Direct visual review of the March 20 raw-stream windows showed multiple wrong or too-coarse labels in the old `data/kimi_labels/*.jsonl` files. A sophisticated model can still produce polished-looking labels that are wrong. Generated labels are hints until a reviewed ledger accepts them.

### 2. Images and logs answer different questions

Tags: `P0` `images` `logs` `review`

Use images for visible truth: page, overlay, modal, tab, and transition settle. Use logs for temporal and causal truth: click timing, source of an overlay, repeated or stuck behavior, and task progression. Neither source is sufficient for every stretch by itself.

### 3. Same-day timestamps are useful, but only as review aids

Tags: `P1` `logs` `review` `artifacts`

`data/raw_stream/*.png` filenames and same-day ALAS log lines can be aligned by wall-clock time. That is useful for selecting windows and checking transitions. It is not proof that every frame has a clean semantic match, because screenshot cadence is sparse and irregular.

### 4. The review unit is a short stretch, not a singleton frame

Tags: `P0` `review` `artifacts`

The useful unit is a contiguous frame window plus a nearby log slice, captured as one reviewed ledger row. This exposes real boundaries and prevents isolated frames from being over-interpreted.

### 5. Kimi prompting must be visible-only and evidence-first

Tags: `P0` `kimi` `prompting`

The prompt should ask for visible text, visible regions, optional closed-set label, confidence, and ambiguity notes. It must explicitly forbid inferring the next destination, intended task, or hidden workflow state. Neighboring frames are valid context, but the answer must still be based on visible evidence.

### 6. Closed-set labels help, but they do not solve ontology collapse

Tags: `P1` `kimi` `ontology`

Kimi can often read the visible UI correctly while still choosing the wrong label from a semantically adjacent set. Closed-set prompting reduces drift, but it does not turn Kimi into a trusted ontology mapper.

### 7. Kimi is useful as a cheap sieve, not the reviewer of record

Tags: `P0` `kimi` `review`

Use Kimi for visible-text extraction, visible-region extraction, provisional labels, and disagreement surfacing across many frames. Do not let Kimi-generated output enter the trusted ledger unless a direct review pass accepts it.

### 8. Preserve provenance when cleaning the corpus

Tags: `P1` `artifacts` `review`

Black-frame and dedupe passes are only trustworthy if they preserve reports of what existed and what was removed or compressed. Cleanup without manifests destroys evidence and makes later review weaker.

### 9. Keep the stable output small

Tags: `P1` `artifacts` `review`

The first stable artifact should be a small reviewed ledger, not another giant JSONL graph. Expand the schema only after repeated review proves which fields are genuinely stable and useful.

## Current Implications

- use [kimi_review.py](/mnt/d/_projects/MasterStateMachine/scripts/kimi_review.py) for cheap evidence extraction, not accepted truth
- store accepted stretch findings in [reviewed_stretches.tsv](/mnt/d/_projects/MasterStateMachine/data/review/reviewed_stretches.tsv)
- grow the state vocabulary from reviewed stretches, not from bulk synthetic labels
