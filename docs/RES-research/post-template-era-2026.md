# The Post-Template Era: Modern UI Detection (March 2026)

> Historical note: moved from `docs/research/post-template-era-2026.md` during the 2026 documentation realignment.


## The Shift

Template matching required exact image patches at fixed resolutions. Modern systems use **visual grounding**—finding UI elements from text descriptions like "commission button with coin icon."

**Key benefit:** Resolution independence. Models output normalized coordinates (0-1000 range) that scale to any screen size.

## The Speed Spectrum

| Approach | Latency | When to Use |
|----------|---------|-------------|
| **YOLO-World** | 20ms | Propose candidate elements |
| **Small VLM** (2-7B) | 200-500ms | Verify specific elements |
| **Full VLM** | 1-5s | Reason when uncertain |

## The Production Pattern

**Most steps:** Use cached relative coordinates from previous successful identifications. No model call.

**Verification step:** If confidence drops, run fast detector or small VLM to confirm "is this still the commission button?"

**Recovery step:** Only when lost—use large VLM to identify current state and replan.

**Result:** 90% of actions execute in <50ms using cached knowledge. Heavy models only for edge cases.

## What Changes in the State Machine

**Old approach:** States defined by pixel colors and template images. Transitions at hardcoded coordinates.

**New approach:** States defined by expected element descriptions. Each element carries a learned relative position (updated when verified). Transitions use cached relative coordinates, refreshed periodically by fast verification.

**State record contains:**
- Text description of what this state looks like
- List of expected elements with descriptions
- Cached relative positions for each element
- Last verification timestamp and confidence

**Transition execution:** Tap at cached relative position → verify screen changed as expected → update cache if element moved slightly.

## Key Insight

The state machine runs on **cached knowledge**, not real-time perception. Visual models are for **learning and recovery**, not every action. This makes thousands of clicks feasible.

---

*Sources: Microsoft OmniParser (2025), ShowUI CVPR 2025, ByteDance UI-TARS.*
