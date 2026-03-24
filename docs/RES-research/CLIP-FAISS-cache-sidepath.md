# CLIP/FAISS Semantic Screenshot Cache Sidepath

> Historical note: this is a research sidepath, not part of the baseline MEmu control plan.

## Status

This is an exploratory optimization note.

It is **not** a requirement for the scrcpy/uiautomator2 MEmu stack.

Use this note only if the baseline loop is working and we later find that latency is the bottleneck.

## Question

Can a strict semantic screenshot cache reduce action latency for repetitive UI states without weakening correctness?

## Short Verdict

**Defer.**

The idea is plausible as a sidepath, but the current repo does not yet have enough evidence to justify moving it into the main plan.

Reasons to defer:

- the primary problem is still getting a reliable MEmu observe-act-observe loop
- the cache only helps if the baseline is already stable
- semantic similarity can be brittle on fine-grained UI states
- CLIP/FAISS are generic image-search tools, not proven UI-state or emulator-state solvers

## What Is Potentially Useful

The useful shape is simple:

- screenshot in
- objective context in
- embedding lookup
- strict hit or miss out
- cached action metadata only on hit
- immediate fall-through to the normal runtime on miss

If this ever becomes real, the hit/miss boundary should stay hard. No fuzzy hints downstream.

## What the Web Research Suggests

Web sources on CLIP and FAISS consistently show the same pattern:

- CLIP is strong for semantic similarity, but it is not instance-precise by default
- FAISS is fast at nearest-neighbor retrieval, but only as good as the embedding space you give it
- semantic caches are common in text/RAG systems, but threshold brittleness and false confidence are recurring failure modes
- UI automation and emulator screenshots add another layer of brittleness because tiny visual differences can matter a lot

Relevant external references reviewed:

- OpenAI Cookbook: CLIP embeddings for multimodal retrieval
- Ultralytics semantic image search with CLIP + FAISS
- FAISS tutorials and docs
- community writeups on semantic caches and their thresholding problems

## What The Repo Evidence Suggests

Local docs point to the same caution:

- `docs/runtime/observation-contracts.md` expects richer context and uncertainty handling, not blind lookup hits
- `docs/memory/2026-03-24-corpus-review-lessons.md` notes that screenshot cadence is sparse and irregular
- `docs/RES-research/RES-stability-trap-analysis.md` shows that the main failure mode is often stability / streak loss, not pure recognition speed
- `docs/ALS-reference/ALS-live-ops.md` emphasizes that noisy capture is a control problem, not just a search problem

That means caching should be treated as a later optimization after the baseline path is already trustworthy.

## If We Ever Build It

If this sidepath becomes worth implementing, the minimum contract should be:

```python
class Tier1Request(BaseModel):
    screenshot_png: bytes
    objective_context: str

class Tier1Result(BaseModel):
    status: Literal["hit", "miss"]
    action: Optional[Literal["TAP", "SWIPE", "WAIT"]] = None
    normalized_coords: Optional[Tuple[float, float]] = None
    cache_entry_id: Optional[str] = None
    similarity_score: Optional[float] = None
    latency_ms: int
```

The important part is the interface shape:

- binary hit/miss
- objective-scoped keys
- no fuzzy hints to the main runtime
- explicit logging of similarity and latency

## Provisional Choices

These are not yet earned:

- CLIP as the embedding model
- FAISS as the index backend
- the exact similarity threshold
- the exact storage layout
- the eviction policy

All of those should be calibrated against the actual Azur Lane UI corpus and emulator behavior before anyone treats them as settled.

## Timing Gate

Only revisit this after:

1. the scrcpy/uiautomator2 baseline loop is stable
2. latency measurements show a real bottleneck
3. we have corpus evidence that a cache would meaningfully reduce repeated decisions

If those gates are not true, keep this as a research note only.