# RES — VLM as Continuous Live Observer

> Historical note: moved from `docs/research/RES-vlm-live-observer.md` during the 2026 documentation realignment.

## Status

This is a design/research document.

It describes a possible live-observer role for the VLM tier. It is not a claim that the current repo already runs this architecture.

See also:
- [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md)
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)
- [RES-vlm-replay-analysis.md](/mnt/d/_projects/MasterStateMachine/docs/RES-research/RES-vlm-replay-analysis.md)

## Core Idea

Instead of using a VLM only for one-off screenshot analysis, treat a small multimodal model as a continuous observer that emits a compact state stream during a session.

The supervisor then reads that stream as compressed visual memory and looks at raw images only when confidence drops or anomalies appear.

## Why This Matters

A continuous observer would make the VLM useful for:

- session memory
- anomaly detection
- rich escalations
- compressed history for the supervisor
- cross-session pattern detection

This is different from asking the model to re-classify every screenshot from scratch.

## Suggested Stream Shape

A useful stream would emit records like:

```json
{"ts": "20260320_134204_477", "page": "page_commission", "conf": 0.97, "note": null}
{"ts": "20260320_134301_044", "page": "unknown", "conf": 0.31, "note": "popup_unrecognized"}
```

Key ideas:
- `page` is a best-effort state/substate label
- `conf` is confidence
- `note` is sparse extra signal about notable visual conditions

## Durable Capabilities This Would Unlock

### Supervisor reads summaries, not raw frames
The runtime can operate mostly on stream summaries and only escalate to screenshots when needed.

### Session memory from visual evidence
A persisted state stream becomes queryable memory about what the system saw over time.

### Anomaly detection
Low confidence, `unknown`, or notable anomaly notes become escalation triggers.

### Rich escalation payloads
Escalation can include recent stream context, candidate explanations, and conflicts between different observation methods.

### Cross-session pattern detection
Repeated anomalies and drift become visible without replaying full image archives manually.

## Post-Template Operating Model

The durable thesis from newer multimodal GUI work is:

- the system should run primarily on cached knowledge and deterministic execution
- visual models should be used for learning, verification, grounding, and recovery
- heavy vision reasoning should be the exception, not the default path for every action

That means a modern runtime should prefer:
- cached relative positions or deterministic transitions when trusted
- smaller/faster models for verification or anomaly notes
- larger models when recovery or deeper reasoning is required

## Proven vs Speculative

### Supported by current model capabilities and research direction
- modern multimodal models can handle multi-image context, grounding, and structured output
- compressed text history is often more useful than re-sending long image sequences blindly
- an always-on observer is architecturally plausible

### Not yet earned in this repo
- a production-quality live stream emitter
- stable thresholds and escalation policy
- trusted operator/runtime contracts consuming that stream

## Practical Use

Use this document for live-observer design thinking and VLM architecture direction.

Do not treat it as a statement that the repo already has a working continuous observer.
