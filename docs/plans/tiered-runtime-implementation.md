# Tiered Runtime Implementation Plan

## Purpose

This document specifies the tactical implementation of the runtime detection and control loop. It answers "how" and "with what" — the end-to-end plan provides strategic context and phasing; this document provides the concrete architecture, interfaces, and implementation details.

See also:
- [end-to-end-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/end-to-end-plan.md) — strategic roadmap and phasing
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md) — near-term priorities
- [memu-fb0-requirements-and-tdd-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/memu-fb0-requirements-and-tdd-plan.md) — first transport slice and validation gates
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md) — runtime ownership boundaries
- [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md) — observation-side contracts

## Activation Boundary

This document does not describe the first transport implementation slice.

It activates only after the current MEmu capture gate has been passed:

- the root-backed `fb0` transport is implemented
- repeated frame capture is proven on the tested instance
- a minimal observe -> act -> verify loop has been demonstrated

Until then, treat this document as downstream architecture, not the next code change.

## Architecture Overview

The runtime uses a 3-tier architecture that balances speed, accuracy, and cost:

```
┌─────────────────────────────────────────────────────────┐
│                      Tier 3: Teacher                    │
│  Large VLM (GPT-4o / Claude) — escalation & distill    │
└────────────────────────┬────────────────────────────────┘
                         │ escalation (rare)
┌────────────────────────▼────────────────────────────────┐
│                      Tier 2: VLM                        │
│  Small VLM (Qwen-VL / Phi-3-Vision) — baseline loop    │
└────────────────────────┬────────────────────────────────┘
                         │ cache miss
┌────────────────────────▼────────────────────────────────┐
│                   Tier 1: Semantic Cache                │
│  CLIP ViT-B/16 + FAISS HNSW + SQLite — fast path       │
└─────────────────────────────────────────────────────────┘
```

**Design principles:**
- VLM-first control loop (Tier 2 is the baseline, not an optional helper)
- Semantic cache (Tier 1) accelerates the common case, never replaces the VLM
- Teacher (Tier 3) handles escalation and populates the cache via distillation
- No MAA foundation — we own the orchestration
- No pipeline religion — we build our own loop

## Tier 1: Semantic Cache

### Purpose

Provide sub-100ms classification for frames that closely match previously-seen states. The cache is an accelerator, not a gatekeeper — it never blocks the VLM path.

### Implementation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Embedding model | CLIP ViT-B/16 | Fast, well-understood, good enough for visual similarity |
| Vector store | FAISS HNSW | Sub-ms search at 100k+ vectors, no server required |
| Metadata store | SQLite | Lightweight, single-file, transactional |
| Storage | `data/cache/` | Embeddings + metadata co-located |

### Request/Response Interface

```python
@dataclass
class Tier1Request:
    frame: np.ndarray                    # BGR frame from emulator
    objective: str                       # Current objective scope (e.g., "daily_missions")
    min_confidence: float = 0.85         # Minimum cache confidence to return

@dataclass
class Tier1Result:
    hit: bool                            # True if cache returned a confident match
    state: Optional[str]                 # Canonical state name (if hit)
    confidence: float                    # Similarity score [0, 1]
    embedding: np.ndarray                # CLIP embedding (always produced)
    cache_key: str                       # Deterministic key for post-action verification
```

### Hit/Hint/Miss Thresholds

| Threshold | Range | Behavior |
|-----------|-------|----------|
| **Hit** | ≥ 0.95 | Return cached state immediately, skip Tier 2 |
| **Hint** | 0.85 – 0.95 | Pass embedding + candidate state to Tier 2 as context |
| **Miss** | < 0.85 | Full Tier 2 classification, no cache assist |

### Objective-Scoped Cache Segmentation

Cache entries are segmented by objective scope. A frame classified during "daily_missions" will not match against cache entries from "commission_collection" unless the embedding similarity is extremely high (≥ 0.97). This prevents cross-contamination between workflows.

```python
# Cache key format: {objective}:{embedding_hash}
cache_key = f"{objective}:{hash(embedding.tobytes())}"
```

### Post-Action Verification

After any action is taken (tap, swipe), the system captures a new frame and verifies:
1. The expected state transition occurred
2. The new frame's embedding matches the expected post-action state

If verification fails, the cache entry is invalidated and the result is flagged for Tier 3 review.

### Cache Population

The cache is populated exclusively through the Tier 3 distillation pipeline. Manual cache writes are not supported — this ensures every cache entry has been vetted by the teacher model.

## Tier 2: VLM Baseline

### Purpose

The primary classification path. Every frame that doesn't get a cache hit goes through Tier 2. This is the control loop's backbone.

### Implementation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Model | Qwen-VL-Chat or Phi-3-Vision | Fast enough for 1-2 fps loop, good accuracy |
| Prompt | Closed-set classification | "Which of these N states is this frame?" with state vocabulary |
| Context | Previous N frames + state history | Temporal consistency |

### Request/Response Interface

```python
@dataclass
class Tier2Request:
    frame: np.ndarray                    # BGR frame from emulator
    objective: str                       # Current objective scope
    state_vocabulary: List[str]          # Allowed state names
    previous_states: List[str]           # Last N states for temporal context
    cache_hint: Optional[Tier1Result]    # Cache hint (if available)

@dataclass
class Tier2Result:
    state: str                           # Classified state name
    confidence: float                    # Model confidence [0, 1]
    reasoning: str                       # Brief explanation from VLM
    needs_escalation: bool               # True if confidence < threshold
    embedding: np.ndarray                # CLIP embedding (for cache write-back)
```

### Escalation Triggers

Tier 2 escalates to Tier 3 when:
- Confidence < 0.70
- State is a recovery/failure class (unknown, popup, stuck, black-frame)
- Temporal consistency check fails (state changed too frequently)
- Cache hint contradicts VLM classification

### Anti-Cheat Measures

To avoid detection by anti-bot systems:
- **Jitter:** Random ±50ms delay between frame capture and classification
- **Random delays:** 200-800ms random delay before action execution
- **Human-like timing:** Action intervals follow a log-normal distribution calibrated to human play sessions
- **Frame skip:** Occasionally skip a frame (1-5% of the time) to simulate human attention lapses

## Tier 3: Teacher / Escalation

### Purpose

Two responsibilities:
1. **Escalation:** Handle ambiguous cases that Tier 2 can't resolve
2. **Distillation:** Generate high-quality classifications to populate the Tier 1 cache

### Implementation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Model | GPT-4o or Claude 3.5 Sonnet | Highest accuracy, worth the cost for rare escalation |
| Trigger | Tier 2 escalation flag | Only called when Tier 2 is uncertain |
| Output | Verified classification + reasoning | Feeds distillation pipeline |

### Escalation Interface

```python
@dataclass
class Tier3Request:
    frame: np.ndarray                    # BGR frame from emulator
    objective: str                       # Current objective scope
    state_vocabulary: List[str]          # Allowed state names
    tier2_result: Tier2Result            # What Tier 2 thought
    previous_states: List[str]           # Temporal context
    cache_hint: Optional[Tier1Result]    # Cache context

@dataclass
class Tier3Result:
    state: str                           # Verified state name
    confidence: float                    # Always ≥ 0.95 (teacher is authoritative)
    reasoning: str                       # Detailed explanation
    is_new_state: bool                   # True if this state wasn't in vocabulary
    suggested_transitions: List[str]     # If new state, what transitions are likely
```

### Distillation Pipeline

The distillation pipeline converts Tier 3 classifications into Tier 1 cache entries:

1. **Capture:** Tier 3 classifies a frame with high confidence
2. **Embed:** Generate CLIP embedding for the frame
3. **Verify:** Post-action verification confirms the classification was correct
4. **Write:** Store embedding + metadata in FAISS + SQLite
5. **Segment:** Tag with objective scope and state name

```
Tier 3 classification → CLIP embedding → post-action verify → cache write
```

### Cost Control

Tier 3 is expensive. Guardrails:
- **Rate limit:** Max 10 Tier 3 calls per minute
- **Budget:** Max 100 Tier 3 calls per hour
- **Fallback:** If budget exhausted, fall back to Tier 2's best guess with a warning
- **Logging:** Every Tier 3 call is logged with full context for review

## Detection Flow

```
frame captured
    │
    ▼
┌─────────────┐     hit (≥ 0.95)      ┌─────────────┐
│  Tier 1     │ ──────────────────────▶│  Return     │
│  Cache      │                        │  cached     │
│  Lookup     │                        │  state      │
└─────┬───────┘                        └─────────────┘
      │ hint (0.85-0.95)
      │ or miss (< 0.85)
      ▼
┌─────────────┐     confident          ┌─────────────┐
│  Tier 2     │ ──────────────────────▶│  Return     │
│  VLM        │     (≥ 0.70)           │  classified │
│  Classify   │                        │  state      │
└─────┬───────┘                        └─────────────┘
      │ uncertain (< 0.70)
      │ or recovery state
      ▼
┌─────────────┐     verified           ┌─────────────┐
│  Tier 3     │ ──────────────────────▶│  Return     │
│  Teacher    │                        │  verified   │
│  Escalate   │                        │  state      │
└─────────────┘                        └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  Distill    │
                                       │  to cache   │
                                       └─────────────┘
```

## Relationship to End-to-End Plan

This document implements the end-to-end plan's:

| End-to-End Phase | Tiered Implementation |
|------------------|----------------------|
| Phase 3: Build State Detection | Tier 2 (VLM baseline) + Tier 1 (semantic cache) |
| Phase 4: Build Live Observation Loop | Tier 2 router + capture pipeline |
| Phase 5: Add Decision and Action | Tier 3 (teacher) for escalation |
| Phase 6: Harden and Expand | Anti-cheat measures, cache tuning, vocabulary expansion |

The end-to-end plan answers "why" and "when"; this document answers "how" and "with what."

## Testing Strategy

### Unit Tests

| Tier | Test | Success Criteria |
|------|------|------------------|
| Tier 1 | Cache hit on identical frame | Returns correct state in < 50ms |
| Tier 1 | Cache miss on novel frame | Returns miss, embedding still produced |
| Tier 1 | Objective segmentation | Cross-objective match requires ≥ 0.97 similarity |
| Tier 2 | Closed-set classification | ≥ 80% accuracy on reviewed ledger frames |
| Tier 2 | Temporal consistency | State doesn't flip-flop across 3 consecutive frames |
| Tier 3 | Escalation resolution | Resolves Tier 2 uncertainty with ≥ 95% accuracy |
| Tier 3 | Distillation write | Cache entry retrievable after distillation |

### Integration Tests

| Test | Success Criteria |
|------|------------------|
| Full detection flow | Cache miss → Tier 2 → Tier 3 → cache write → subsequent hit |
| Post-action verification | Action produces expected state transition |
| Anti-cheat timing | Action intervals pass Kolmogorov-Smirnov test vs. human distribution |
| Cost control | Tier 3 rate limit enforced, fallback works |

### Evaluation Protocol

1. **Leave-one-out:** For each reviewed ledger frame, classify with all other frames as reference
2. **Temporal sequences:** Test on consecutive frame sequences, not isolated frames
3. **Recovery coverage:** Ensure recovery states (unknown, popup, stuck) are tested
4. **Catastrophic misclassification:** Track cases where recovery state is classified as stable (or vice versa) — must be ≤ 5%

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CLIP embeddings too coarse | Fine-tune CLIP on reviewed ledger frames; fall back to VLM-only if accuracy < 70% |
| FAISS index corruption | Daily backup of index + metadata; rebuild from distillation log if corrupted |
| Tier 3 cost explosion | Hard rate limit + budget cap; degrade gracefully to Tier 2-only |
| Cache staleness | TTL on cache entries (7 days); invalidate on post-action verification failure |
| Anti-cheat detection | Randomize all timing parameters; never use fixed delays; calibrate against human play data |
| State vocabulary explosion | Cap at 50 states; merge rare states into "other" category; expand only with Tier 3 justification |

## Implementation Order

1. **Tier 2 VLM baseline** — get basic classification working
2. **Tier 1 cache (read-only)** — add cache lookup, no writes yet
3. **Tier 3 escalation** — handle Tier 2 uncertainty
4. **Distillation pipeline** — enable cache writes from Tier 3
5. **Post-action verification** — add cache invalidation
6. **Anti-cheat measures** — add timing randomization
7. **Objective segmentation** — scope cache by workflow
8. **Cost controls** — add rate limits and budget caps

Each step is independently testable and deployable. The system is useful after step 2; steps 3-8 add robustness and efficiency.

## Purpose

This document specifies the tactical implementation of the runtime detection and control loop. It answers "how" and "with what" — the end-to-end plan provides strategic context and phasing; this document provides the concrete architecture, interfaces, and implementation details.

See also:
- [end-to-end-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/end-to-end-plan.md) — strategic roadmap and phasing
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md) — near-term priorities
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md) — runtime ownership boundaries
- [observation-contracts.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/observation-contracts.md) — observation-side contracts

## Architecture Overview

The runtime uses a 3-tier architecture that balances speed, accuracy, and cost:

```
┌─────────────────────────────────────────────────────────┐
│                      Tier 3: Teacher                    │
│  Large VLM (GPT-4o / Claude) — escalation & distill    │
└────────────────────────┬────────────────────────────────┘
                         │ escalation (rare)
┌────────────────────────▼────────────────────────────────┐
│                      Tier 2: VLM                        │
│  Small VLM (Qwen-VL / Phi-3-Vision) — baseline loop    │
└────────────────────────┬────────────────────────────────┘
                         │ cache miss
┌────────────────────────▼────────────────────────────────┐
│                   Tier 1: Semantic Cache                │
│  CLIP ViT-B/16 + FAISS HNSW + SQLite — fast path       │
└─────────────────────────────────────────────────────────┘
```

**Design principles:**
- VLM-first control loop (Tier 2 is the baseline, not an optional helper)
- Semantic cache (Tier 1) accelerates the common case, never replaces the VLM
- Teacher (Tier 3) handles escalation and populates the cache via distillation
- No MAA foundation — we own the orchestration
- No pipeline religion — we build our own loop

## Tier 1: Semantic Cache

### Purpose

Provide sub-100ms classification for frames that closely match previously-seen states. The cache is an accelerator, not a gatekeeper — it never blocks the VLM path.

### Implementation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Embedding model | CLIP ViT-B/16 | Fast, well-understood, good enough for visual similarity |
| Vector store | FAISS HNSW | Sub-ms search at 100k+ vectors, no server required |
| Metadata store | SQLite | Lightweight, single-file, transactional |
| Storage | `data/cache/` | Embeddings + metadata co-located |

### Request/Response Interface

```python
@dataclass
class Tier1Request:
    frame: np.ndarray                    # BGR frame from emulator
    objective: str                       # Current objective scope (e.g., "daily_missions")
    min_confidence: float = 0.85         # Minimum cache confidence to return

@dataclass
class Tier1Result:
    hit: bool                            # True if cache returned a confident match
    state: Optional[str]                 # Canonical state name (if hit)
    confidence: float                    # Similarity score [0, 1]
    embedding: np.ndarray                # CLIP embedding (always produced)
    cache_key: str                       # Deterministic key for post-action verification
```

### Hit/Hint/Miss Thresholds

| Threshold | Range | Behavior |
|-----------|-------|----------|
| **Hit** | ≥ 0.95 | Return cached state immediately, skip Tier 2 |
| **Hint** | 0.85 – 0.95 | Pass embedding + candidate state to Tier 2 as context |
| **Miss** | < 0.85 | Full Tier 2 classification, no cache assist |

### Objective-Scoped Cache Segmentation

Cache entries are segmented by objective scope. A frame classified during "daily_missions" will not match against cache entries from "commission_collection" unless the embedding similarity is extremely high (≥ 0.97). This prevents cross-contamination between workflows.

```python
# Cache key format: {objective}:{embedding_hash}
cache_key = f"{objective}:{hash(embedding.tobytes())}"
```

### Post-Action Verification

After any action is taken (tap, swipe), the system captures a new frame and verifies:
1. The expected state transition occurred
2. The new frame's embedding matches the expected post-action state

If verification fails, the cache entry is invalidated and the result is flagged for Tier 3 review.

### Cache Population

The cache is populated exclusively through the Tier 3 distillation pipeline. Manual cache writes are not supported — this ensures every cache entry has been vetted by the teacher model.

## Tier 2: VLM Baseline

### Purpose

The primary classification path. Every frame that doesn't get a cache hit goes through Tier 2. This is the control loop's backbone.

### Implementation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Model | Qwen-VL-Chat or Phi-3-Vision | Fast enough for 1-2 fps loop, good accuracy |
| Prompt | Closed-set classification | "Which of these N states is this frame?" with state vocabulary |
| Context | Previous N frames + state history | Temporal consistency |

### Request/Response Interface

```python
@dataclass
class Tier2Request:
    frame: np.ndarray                    # BGR frame from emulator
    objective: str                       # Current objective scope
    state_vocabulary: List[str]          # Allowed state names
    previous_states: List[str]           # Last N states for temporal context
    cache_hint: Optional[Tier1Result]    # Cache hint (if available)

@dataclass
class Tier2Result:
    state: str                           # Classified state name
    confidence: float                    # Model confidence [0, 1]
    reasoning: str                       # Brief explanation from VLM
    needs_escalation: bool               # True if confidence < threshold
    embedding: np.ndarray                # CLIP embedding (for cache write-back)
```

### Escalation Triggers

Tier 2 escalates to Tier 3 when:
- Confidence < 0.70
- State is a recovery/failure class (unknown, popup, stuck, black-frame)
- Temporal consistency check fails (state changed too frequently)
- Cache hint contradicts VLM classification

### Anti-Cheat Measures

To avoid detection by anti-bot systems:
- **Jitter:** Random ±50ms delay between frame capture and classification
- **Random delays:** 200-800ms random delay before action execution
- **Human-like timing:** Action intervals follow a log-normal distribution calibrated to human play sessions
- **Frame skip:** Occasionally skip a frame (1-5% of the time) to simulate human attention lapses

## Tier 3: Teacher / Escalation

### Purpose

Two responsibilities:
1. **Escalation:** Handle ambiguous cases that Tier 2 can't resolve
2. **Distillation:** Generate high-quality classifications to populate the Tier 1 cache

### Implementation

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Model | GPT-4o or Claude 3.5 Sonnet | Highest accuracy, worth the cost for rare escalation |
| Trigger | Tier 2 escalation flag | Only called when Tier 2 is uncertain |
| Output | Verified classification + reasoning | Feeds distillation pipeline |

### Escalation Interface

```python
@dataclass
class Tier3Request:
    frame: np.ndarray                    # BGR frame from emulator
    objective: str                       # Current objective scope
    state_vocabulary: List[str]          # Allowed state names
    tier2_result: Tier2Result            # What Tier 2 thought
    previous_states: List[str]           # Temporal context
    cache_hint: Optional[Tier1Result]    # Cache context

@dataclass
class Tier3Result:
    state: str                           # Verified state name
    confidence: float                    # Always ≥ 0.95 (teacher is authoritative)
    reasoning: str                       # Detailed explanation
    is_new_state: bool                   # True if this state wasn't in vocabulary
    suggested_transitions: List[str]     # If new state, what transitions are likely
```

### Distillation Pipeline

The distillation pipeline converts Tier 3 classifications into Tier 1 cache entries:

1. **Capture:** Tier 3 classifies a frame with high confidence
2. **Embed:** Generate CLIP embedding for the frame
3. **Verify:** Post-action verification confirms the classification was correct
4. **Write:** Store embedding + metadata in FAISS + SQLite
5. **Segment:** Tag with objective scope and state name

```
Tier 3 classification → CLIP embedding → post-action verify → cache write
```

### Cost Control

Tier 3 is expensive. Guardrails:
- **Rate limit:** Max 10 Tier 3 calls per minute
- **Budget:** Max 100 Tier 3 calls per hour
- **Fallback:** If budget exhausted, fall back to Tier 2's best guess with a warning
- **Logging:** Every Tier 3 call is logged with full context for review

## Detection Flow

```
frame captured
    │
    ▼
┌─────────────┐     hit (≥ 0.95)      ┌─────────────┐
│  Tier 1     │ ──────────────────────▶│  Return     │
│  Cache      │                        │  cached     │
│  Lookup     │                        │  state      │
└─────┬───────┘                        └─────────────┘
      │ hint (0.85-0.95)
      │ or miss (< 0.85)
      ▼
┌─────────────┐     confident          ┌─────────────┐
│  Tier 2     │ ──────────────────────▶│  Return     │
│  VLM        │     (≥ 0.70)           │  classified │
│  Classify   │                        │  state      │
└─────┬───────┘                        └─────────────┘
      │ uncertain (< 0.70)
      │ or recovery state
      ▼
┌─────────────┐     verified           ┌─────────────┐
│  Tier 3     │ ──────────────────────▶│  Return     │
│  Teacher    │                        │  verified   │
│  Escalate   │                        │  state      │
└─────────────┘                        └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  Distill    │
                                       │  to cache   │
                                       └─────────────┘
```

## Relationship to End-to-End Plan

This document implements the end-to-end plan's:

| End-to-End Phase | Tiered Implementation |
|------------------|----------------------|
| Phase 3: Build State Detection | Tier 2 (VLM baseline) + Tier 1 (semantic cache) |
| Phase 4: Build Live Observation Loop | Tier 2 router + capture pipeline |
| Phase 5: Add Decision and Action | Tier 3 (teacher) for escalation |
| Phase 6: Harden and Expand | Anti-cheat measures, cache tuning, vocabulary expansion |

The end-to-end plan answers "why" and "when"; this document answers "how" and "with what."

## Testing Strategy

### Unit Tests

| Tier | Test | Success Criteria |
|------|------|------------------|
| Tier 1 | Cache hit on identical frame | Returns correct state in < 50ms |
| Tier 1 | Cache miss on novel frame | Returns miss, embedding still produced |
| Tier 1 | Objective segmentation | Cross-objective match requires ≥ 0.97 similarity |
| Tier 2 | Closed-set classification | ≥ 80% accuracy on reviewed ledger frames |
| Tier 2 | Temporal consistency | State doesn't flip-flop across 3 consecutive frames |
| Tier 3 | Escalation resolution | Resolves Tier 2 uncertainty with ≥ 95% accuracy |
| Tier 3 | Distillation write | Cache entry retrievable after distillation |

### Integration Tests

| Test | Success Criteria |
|------|------------------|
| Full detection flow | Cache miss → Tier 2 → Tier 3 → cache write → subsequent hit |
| Post-action verification | Action produces expected state transition |
| Anti-cheat timing | Action intervals pass Kolmogorov-Smirnov test vs. human distribution |
| Cost control | Tier 3 rate limit enforced, fallback works |

### Evaluation Protocol

1. **Leave-one-out:** For each reviewed ledger frame, classify with all other frames as reference
2. **Temporal sequences:** Test on consecutive frame sequences, not isolated frames
3. **Recovery coverage:** Ensure recovery states (unknown, popup, stuck) are tested
4. **Catastrophic misclassification:** Track cases where recovery state is classified as stable (or vice versa) — must be ≤ 5%

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CLIP embeddings too coarse | Fine-tune CLIP on reviewed ledger frames; fall back to VLM-only if accuracy < 70% |
| FAISS index corruption | Daily backup of index + metadata; rebuild from distillation log if corrupted |
| Tier 3 cost explosion | Hard rate limit + budget cap; degrade gracefully to Tier 2-only |
| Cache staleness | TTL on cache entries (7 days); invalidate on post-action verification failure |
| Anti-cheat detection | Randomize all timing parameters; never use fixed delays; calibrate against human play data |
| State vocabulary explosion | Cap at 50 states; merge rare states into "other" category; expand only with Tier 3 justification |

## Implementation Order

1. **Tier 2 VLM baseline** — get basic classification working
2. **Tier 1 cache (read-only)** — add cache lookup, no writes yet
3. **Tier 3 escalation** — handle Tier 2 uncertainty
4. **Distillation pipeline** — enable cache writes from Tier 3
5. **Post-action verification** — add cache invalidation
6. **Anti-cheat measures** — add timing randomization
7. **Objective segmentation** — scope cache by workflow
8. **Cost controls** — add rate limits and budget caps

Each step is independently testable and deployable. The system is useful after step 2; steps 3-8 add robustness and efficiency.
