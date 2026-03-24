# VLM Replay Analysis Research

> Historical note: moved from `docs/research/RES-vlm-replay-analysis.md` during the 2026 documentation realignment.

## Status

This is a research foundation document.

It captures replay/corpus analysis patterns that matter to the project. It is not a direct implementation plan.

See also:
- [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md)
- [RES-vlm-live-observer.md](/mnt/d/_projects/MasterStateMachine/docs/RES-research/RES-vlm-live-observer.md)
- [alas-build-plan.md](/mnt/d/_projects/MasterStateMachine/docs/prework/alas-build-plan.md)

## Problem

Given screenshots, logs, and traces, the repo needs ways to:

1. classify what is on screen
2. recover useful state-transition information from recorded sessions
3. understand failure modes from before/after evidence
4. decide what history and context a VLM should actually see

## Durable Findings

### Interleaved image-text timelines are useful
Chronological screenshot/action sequences are a workable way to let a VLM read a session as a narrative.

### Compressed history is better than dumping every image
Text summaries of prior context can carry more useful history than re-sending long raw image sequences.

### Keyframe extraction matters
Not every frame is worth classifying. Transition points and changed frames are far higher-value than repeated identical screenshots.

### Before/after reflection is high leverage
Pairs of frames plus the action between them are especially useful for determining whether an action succeeded or failed.

### Trace-to-graph extraction is plausible
Session traces can be converted into `(source, action, target)` style artifacts, but this should be treated as an extraction aid, not automatic truth.

## Implications For This Repo

The replay path should favor:
- keyframe-oriented corpus processing
- structured outputs for classification/extraction tasks
- short image windows plus text history
- explicit before/after analysis for failures

## Proven vs Speculative

### Reasonable to rely on
- replay analysis is useful for understanding failures and building better labels
- full-frame brute force over every image is a poor default
- structured outputs make replay work more reliable

### Not yet earned here
- a complete replay-to-graph pipeline
- a fully trusted automated graph-construction loop from traces alone

## Practical Use

Use this document to guide replay/corpus analysis design.

Do not treat it as a commitment that every referenced research pattern belongs in the shipped system.
