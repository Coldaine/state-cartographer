# Tiered Runtime Implementation Plan (Borrowed Substrate and VLM)

Status: design proposal, aligned to the repo’s current rebuild posture.

See also:
- [todo.md](/mnt/d/_projects/MasterStateMachine/docs/todo.md)

## Purpose

Deliver a supervised Android/Unity automation runtime with three escalating tiers:
- Tier 2 baseline: direct VLM grounding loop for every action.
- Tier 1 semantic cache: fast retrieval for repeated states once data proves repeatability.
- Tier 3 teacher: larger-model recovery and distillation for novel/recovery situations.

The stack is conservative by design: correctness and verification are preferred over shortcut speed.

The runtime should borrow the external control substrate for attachment, frame access, and input primitives instead of owning that transport itself.

This document is the canonical owner of runtime architecture and phased implementation sequencing.

## Target Runtime Responsibilities

- receive frames and actions through borrowed control tools
- package objective context
- route through tiered resolver logic
- validate proposed actions
- execute actions through borrowed tools
- validate post-action transition
- escalate with structured context when uncertainty is high
- recover from failure modes instead of continuing blindly

## Phase 1 — Baseline VLM loop (Tier 2 only)

Goal: prove stable observe-act-observe loop on real device using borrowed substrate.

- Input: frame plus task instruction
- Model path: local VLM via OpenAI-compatible endpoint (e.g. Qwen-style local image model)
- Output contract: strict geometry + confidence JSON (coordinates normalized 0-1)
- Sanity checks:
  - found flag present
  - bbox valid (`x2 > x1`, `y2 > y1`, within image bounds)
  - reasonable box size (not inverted, not full-screen for point actions)
  - confidence above min threshold
- Retry:
  - attempt 1 with original instruction
  - attempt 2 with explicit full-screen search language if first attempt fails
- Execution:
  - convert normalized coords to pixels
  - use the borrowed control tool to tap, swipe, key, or text
  - capture follow-up frame and verify transition
- Escalation:
  - repeated fails or clear uncertainty package structured context for Tier 3
- Success criteria:
  - per-action latency and failure profile baseline established
  - stable control on at least one real workflow

## Phase 2 — Semantic Embedding Cache (Tier 1)

Goal: speed up repeated states without reducing safety.

- Encoder: pretrained vision encoder (CLIP ViT-B/16 expected initially)
- Index: FAISS (HNSW) over normalized embeddings
- Metadata store: objective tag, action, normalized target coordinates, post-action expectation, stats
- Lookup outputs:
  - `hit`: similarity >= tuned threshold -> execute with post-action verification
  - `hint`: mid-range similarity -> pass hint to Tier 2 for narrowed search and verification
  - `miss`: low similarity -> full Tier 2 grounding
- Objective scoping:
  - cache entries keyed by `objective_tag` to prevent context contamination
- Safety:
  - all cache hits still require post-action verification
  - mismatches trigger invalidation/escalation rather than blind action
- Insertion policy:
  - only insert after successful Tier 3 resolution, and only after confidence/stability checks
  - collision checks against nearest neighbors before insertion

## Phase 3 — Distillation and Teacher Escalation (Tier 3)

- Escalation conditions:
  - Tier 2 fails after retry
  - repeated retries indicate stuck state
- Teacher responsibilities:
  - reason over recent frames and objective
  - return trajectory when needed (not only single tap)
  - execute recovery actions for blocking states (popup-dismiss, back, restart flow)
- Distillation:
  - store pre/post-action embeddings and action metadata on verified success
  - mark ambiguous entries when collision risk exists and force future verification as needed

## Threshold Calibration

Start conservative and tune against real data:
- hit threshold high enough to prevent false positives (often 0.95–0.98 depending encoder)
- hint band only if false positive risk stays acceptably low
- fallback-only behavior is acceptable when hints are not yet reliable

## Risk Controls

- false actions from caches: mitigated by high thresholds and post-action verification
- embedding collisions: top-k neighbor checks and objective scoping
- stale cache on UI updates: time/version-based pruning and miss recovery behavior
- anti-cheat: jitter + delay jitter at execution layer
- resource risk: keep VLM quantized and cache size bounded by objective segmentation

## Testing Priorities

- phase 1: schema checks, coordinate sanity, live device latency, retry/escalation rates
- phase 2: intra-class similarity stability, inter-class separation, hit/hint/miss behavior, cache invalidation
- phase 3: novelty recovery correctness and distillation replay behavior

## Detailed Execution Roadmap

The near-term implementation order should be:

1. stabilize the borrowed-substrate baseline
   - prove the external control tool can attach and remain healthy
   - prove the preferred visual substrate can provide current frames or a suitable operator/debug stream
   - capture and action dispatch through borrowed tools
   - before/after artifact persistence per run
2. turn Tier 2 into a stronger resolver
   - explicit request/response contracts
   - schema hardening and retry behavior
   - post-action verification stronger than raw pixel diff
3. build a real session loop
   - repeated observe-act-observe execution
   - stuck detection
   - recovery primitives
   - structured JSONL run logs
4. split implementation boundaries
   - actor
   - verifier
   - session/runtime
   - future cache layer
5. instrument the baseline before cache work
   - repeated-screen statistics
   - success/failure clustering
   - latency and confidence distributions
6. add semantic Tier 1 only after baseline data supports it
   - CLIP-style embeddings
   - FAISS lookup
   - objective-scoped metadata
   - hit/hint/miss routing
   - post-hit verification and invalidation
7. add Tier 3 after Tier 1 and Tier 2 boundaries are stable
   - novelty recovery
   - multi-step trajectories
   - controlled distillation back into Tier 1

## Detailed Phase 1 Expectations

Phase 1 should specifically deliver:

- a borrowed-control-tool interface that can:
  - attach to the pinned MEmu instance
  - provide screenshot/frame access
  - dispatch tap/swipe/key/text primitives
- a Tier-2-first resolver path that:
  - uses strict geometry validation
  - retries once with broader search language
  - returns structured failure reasons
- a thin live command path that:
  - captures
  - resolves
  - executes
  - captures again
  - verifies basic transition
- artifact capture for debugging:
  - before image/frame
  - after image/frame
  - structured result JSON

## Concrete Next Steps After Current Slice

After the borrowed substrate is proven, the next implementation steps should be:

1. replace cheap frame-diff verification with a stronger semantic verifier
2. add a multi-step `run-objective` loop with retry and stuck handling
3. persist step-by-step runtime events as JSONL
4. analyze real run artifacts to decide where semantic caching is justified
5. implement semantic Tier 1 with hit/miss first, then hints if measurements justify them

## Immediate Next Step

The next implementation priority is:

1. strengthen post-action verification in runtime code
   - keep pixel diff as a cheap signal only
   - add a semantic verifier path that can judge whether the intended UI change actually happened
2. add a multi-step `run-objective` loop
   - capture
   - resolve
   - execute
   - verify
   - retry
   - detect stuck states
   - emit structured JSONL run logs plus screenshots
3. collect run artifacts before semantic cache work
   - before/after screenshots
   - chosen coordinates
   - verification result
   - latency and confidence signals

This is the point where the borrowed-substrate scaffold becomes a real runtime slice rather than a single-action helper.

## Transport Status Update

The real-device transport proof was completed on `2026-03-25` against the pinned MEmu instance.

- Maa/ADB path: accepted for the current transport slice
- scrcpy: `debug_only` on this Windows setup
- next-slice runtime observation path: ADB screencap via adbutils
- next implementation focus: stronger verification and the multi-step runtime loop above transport

## Current Positioning

This is a staged implementation target. The repo currently includes early scaffolding but not a full live trusted runtime.

Companion docs:
- the MEmu note owns emulator transport/integration constraints
- the runtime policy docs own current prototype truth and alignment gaps
