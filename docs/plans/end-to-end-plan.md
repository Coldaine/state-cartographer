# End-to-End Plan: Corpus to Runtime

## Purpose

This document describes the full chain from where the project is now to a working autonomous runtime. It exists because no single document previously connected the dots from "review corpus windows" through to "ship a state machine that controls the game."

See also:
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [corpus-review-playbook.md](/mnt/d/_projects/MasterStateMachine/docs/prework/corpus-review-playbook.md)
- [north-star.md](/mnt/d/_projects/MasterStateMachine/docs/project/north-star.md)
- [memu-android-control-stack-2026-03-24.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-android-control-stack-2026-03-24.md)
- [memu-fb0-requirements-and-tdd-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-fb0-requirements-and-tdd-plan.md)
- [tiered-runtime-implementation.md](/mnt/d/_projects/MasterStateMachine/docs/plans/tiered-runtime-implementation.md) — tactical implementation of Phases 3-5

## Where We Are Now

- 1 completed ledger row in `data/review/reviewed_stretches.tsv`
- 5 seed windows queued for review (all raw_stream)
- ~28,800 screenshots in `data/raw_stream/` with matching ALAS logs (spanning 2026-03-20 through 2026-03-24)
- `kimi_review.py` available as cheap VLM first-pass tool
- ALAS reference system available under `vendor/AzurLaneAutoScript/`
- direct MEmu `fb0` capture has been proven on `127.0.0.1:21513`, but the full observe-act-verify control slice is not yet proven
- Prior attempt at automated observation (ALAS-Observe) failed completely — pixel-color matching against a generated graph.json produced 100% unknown results

## What Failed and Why

Two prior approaches failed:

1. **Generated JSONL labels** — ALAS logs + Kimi vision were used to auto-generate state labels for the corpus. These were never verified against actual frames and turned out to be fake structure built on unverified inference.

2. **ALAS-Observe pixel matching** — A runtime observer tried to classify screenshots by checking individual pixel colors at specific coordinates. This was too brittle to match anything and produced 100% unknown results across all sessions.

Both failures share the same root cause: trying to shortcut the "what states actually exist and what do they look like" question without grounding answers in direct visual evidence.

## The Plan

### Phase 1: Build Trusted Ground Truth (current phase)

**Goal:** Produce enough human-verified ledger rows to derive a state vocabulary and transition graph.

**Method:**
1. For each seed window, run a two-pass review:
   - Pass 1: Kimi via `kimi_review.py` — cheap VLM for visible text, regions, provisional labels
   - Pass 2: Claude direct image review — compare against Kimi output and ALAS log slice
   - Optional Pass 3: Codex or Gemini on disputed frames as tiebreaker
2. Produce one ledger row per window in `data/review/reviewed_stretches.tsv`
3. Each row records: what was visibly true, what changed, what the log knew correctly, what the machine labels got wrong

**Exit gate:** Coverage, not count. Minimum:
- 12-20 quality rows
- Covering 6-10 distinct visual states
- Covering at least 3 recovery/failure classes
- Covering both stable states and transition windows

**Output:** A populated `reviewed_stretches.tsv` with enough coverage to support Phase 2.

### Phase 2: Derive State Vocabulary and Transition Graph

**Goal:** Extract from the ledger rows a concrete, canonical set of states and transitions.

**Method:**
1. Read all ledger rows and extract every distinct visual state that appears
2. Assign canonical names — collapse ALAS's 100+ page IDs into the ~20-40 states that actually matter for decision-making
3. Record transitions: which states connect, what triggers them, what evidence distinguishes them
4. Identify recovery categories: unknown, popup, stuck, black-frame, restart/relogin
5. Identify where the state vocabulary is still uncertain or undersampled

**Exit gate:** A written `state_machine_v0` spec that includes:
- Canonical state definitions with visual descriptions
- Allowed transitions with trigger/evidence requirements
- Guard conditions (what must be true before acting)
- Fallback/recovery edges
- Every state backed by at least one reviewed ledger row

**Output:** `docs/runtime/state-machine-v0.md` (or equivalent structured format)

**Open question:** What format should the spec take? Markdown? YAML? A graph.json that's actually grounded this time? Decide before starting Phase 2.

### Phase 2.5: Detection Spike (time-boxed)

**Goal:** Before committing to a detection approach, prove one can work.

This exists because two prior approaches (pixel matching, generated labels) failed without validation. Do not repeat the pattern of listing approaches without testing them.

**Method:**
1. Take 10-15 reviewed ledger frames from Phase 1
2. Run a time-boxed spike (2-3 days) testing:
   - `vlm_detector.py` `detect_page()` — already exists in `scripts/vlm_detector.py`, does VLM closed-set classification with multi-image context
   - CLIP embedding similarity — embed reference frames, classify by nearest-neighbor
   - OCR text extraction — check if visible text alone discriminates states
3. Produce quantitative accuracy numbers for each approach

**Exit gate:** At least one approach exceeds 70% accuracy on the test set. If none do, simplify the state vocabulary before proceeding.

**Output:** A decision on which detection approach to use in Phase 3, backed by numbers.

### Phase 3: Build State Detection

**Goal:** Make a machine that can look at a frame and say which state it's in.

This is the hardest engineering problem. The ledger tells us what states exist; this phase makes them machine-detectable.

**Prior art:** `scripts/vlm_detector.py` already implements `detect_page()` — VLM closed-set classification with dual-model adjudication. This is the obvious starting point, not a blank-slate design problem.

**Approach:** Decided by the Phase 2.5 spike. Candidates:
- **VLM classification** — send frame to a small VLM, ask "which of these N states is this?" with the state vocabulary as a closed set. Simple but slow and API-dependent.
- **OCR + heuristics** — most Azur Lane screens have distinctive text. Fast OCR (PaddleOCR/EasyOCR) could identify states by visible text alone for 80-90% of cases.
- **CLIP embedding similarity** — embed reference frames for each state, classify new frames by nearest-neighbor. Could use the ledger's reviewed frames as the reference set.
- **Hybrid** — OCR for the easy cases, VLM for ambiguous cases. This is effectively the two-tier pipeline.

**Exit gate:** The classifier correctly identifies the canonical state for >=80% of reviewed ledger frames when evaluated leave-one-out, with <=5% catastrophic misclassification (identifying a recovery state as a stable state or vice versa).

**Open question:** The ledger provides ~20 verified frames, but the full corpus has ~28,800. Once the state vocabulary exists, the larger corpus can be used to find more examples per state via embedding search — the ledger frames are the seed, not the ceiling.

**Output:** A working detection function: `frame -> (state, confidence)`

### Parallel Workstream: MEmu Control Stack Proof

**Goal:** Prove the emulator screenshot/action pipeline works before anything depends on it.

This runs alongside Phases 1-2, not after them. DroidCast previously caused black-frame floods that paralyzed the bot. Since then, one direct proof has been re-earned: root-backed `fb0` capture can return a non-black Azur Lane frame on the tested MEmu instance. What remains unproven is turning that fact into a repeatable transport plus action-verification slice.

**Exit gate:** the verified `fb0` path can:
- capture 100 consecutive exact-size, decodable, non-near-black frames from MEmu at >=1 fps without manual intervention
- keep channel-order handling explicit and validated on the tested emulator image
- support at least one observe -> act -> verify slice in which a dispatched action yields a measurable frame change

If this fails, re-evaluate whether the failure is in transport implementation, emulator variability, or the need for a different capture backend.

### Phase 4: Build Live Observation Loop

**Goal:** A runtime that captures frames from the emulator and classifies them in real-time.

**Depends on:**
- Phase 3 (state detection works)
- MEmu control stack proof (can capture repeated screenshots from the emulator and verify at least one action outcome)

**Method:**
1. Wire proven MEmu capture into a classification loop: capture -> classify -> log
2. Wire detection into a loop: capture -> classify -> log
3. Run observation-only alongside ALAS — don't act, just watch and record what the observer thinks vs what ALAS does
4. Compare observer classifications against ALAS's own page detection in real-time

**Exit gate:** The observer can run alongside ALAS for a full daily cycle and produce a classification log that is more accurate than ALAS's own `unknown` rate.

**Output:** A running observation loop with classification logs.

### Phase 5: Add Decision and Action

**Goal:** The observer stops just watching and starts deciding what to do.

**Depends on:**
- Phase 4 (observation works)
- State machine v0 spec (knows what transitions are allowed)
- ALAS button/coordinate knowledge (knows where to tap)

**Method:**
1. Implement the transition graph from the v0 spec as executable logic
2. Use ALAS's `assets` folder for button coordinates and tap targets as a starting point — but verify coordinates against live screenshots, as prior work found ALAS coordinates "diverged noticeably" on some controls
3. Start with a single linear workflow (e.g., daily missions) as the first automation target
4. Run with human supervision — the bot proposes actions, human confirms until trust is earned

**Exit gate:** Can complete one full daily-mission cycle autonomously with human oversight.

**Output:** A supervised automation runtime.

### Phase 6: Harden and Expand

**Goal:** Make it robust and expand to more workflows.

This phase is deliberately vague because it depends on everything before it. Key concerns:
- Recovery handling when classification confidence is low
- VLM escalation for genuinely ambiguous states
- Expanding the state vocabulary as new workflows reveal new states
- Recording what happens during runs to grow the corpus

## Critical Risks and Open Questions

1. **Detection gap:** The plan assumes we can build a reliable state classifier. Phase 2.5 exists specifically to test this before committing. If no approach exceeds 70% on the spike, simplify the vocabulary before proceeding.

2. **Corpus density:** ~28,800 raw_stream screenshots is a large corpus, but coverage of specific states may be uneven. Once the vocabulary exists, embedding search can find more examples per state without manual review.

3. **MEmu control stack:** The screenshot/action pipeline is only partially proven. The old DroidCast path failed badly enough to matter, while the new root-backed `fb0` path has only been proven for direct frame capture on one tested instance. The parallel MEmu workstream must still prove repeated capture stability, channel-order validation, focus handling, and action verification before Phase 4 can start.

4. **Transition vs state:** Knowing what states exist is easier than knowing when transitions happen. The hardest runtime problem is "am I still transitioning or have I arrived?" The ledger captures some of this, but the temporal resolution may not be enough.

5. **Scale of state vocabulary:** The plan estimates 20-40 states. If the real number is 100+ (like ALAS), the classifier problem gets much harder. The ledger should reveal the actual scale.
