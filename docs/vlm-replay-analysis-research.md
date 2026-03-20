# VLM Replay Analysis Research

Research compiled 2026-03-20 for State Cartographer's vision pipeline.

## Problem

We have a growing corpus of game screenshots + ALAS automation logs. We need to:
1. Classify what's on screen (page identification)
2. Build a state transition graph from observations
3. Understand failure modes (why the bot gets stuck)
4. Eventually enable Claude to drive the game using the state machine

## Our setup

- **Big VLM**: Qwen3.5-9B-AWQ at localhost:18900, 128k context, vision capable
- **Small VLM (planned)**: Qwen3.5-2B or 0.8B for always-on classification
- **Screenshot corpus**: ~2,000 valid frames in data/raw_stream/ (black frames cleaned)
- **ALAS logs**: Timestamped action/page/error events
- **Token budget**: 1280x720 screenshot = ~1,175 tokens per image. ~105 frames fit in 128k context at full res.

## Prompt patterns for feeding screenshots + logs to a VLM

### Pattern 1: Interleaved image-text streaming

Feed chronological screenshot-action pairs as a sequence:

```
[screenshot_1] Action: click(741, 692) @ MAIN_GOTO_RESHMENU
[screenshot_2] Action: click(362, 368) @ RESHMENU_GOTO_RESEARCH
[screenshot_3] Action: Page arrive: page_research
[screenshot_4] ...
```

The VLM reads this like a narrative. Works with any vision model — it's a prompt structure, not a model feature. ShowUI (CVPR 2025) and UI-TARS (ByteDance, Jan 2025) both use this pattern for GUI agent inference.

**Key finding from ShowUI**: History of 2 prior screenshot-action pairs is sufficient for most navigation tasks. More history helps on in-distribution tasks but hurts generalization.

- Source: [ShowUI (CVPR 2025)](https://arxiv.org/abs/2411.17465)
- Source: [UI-TARS (ByteDance)](https://arxiv.org/abs/2501.12326)

### Pattern 2: History compression (text replaces images)

Only the current screenshot needs to be an image. Prior history is carried as text summaries. This is how Mobile-Agent-v2 (NeurIPS 2024) handles long sessions:

- A planning agent converts screenshot-action history into a text "task progress" summary
- Only the current screenshot is sent as an image
- 30%+ improvement over keeping all screenshots in context

**Relevance for us**: The small VLM's output stream (`{timestamp, page_id}`) is already compressed history. Claude reads the text stream and only looks at actual images when something unexpected happens.

- Source: [Mobile-Agent-v2 (NeurIPS 2024)](https://arxiv.org/abs/2406.01014)

### Pattern 3: Keyframe extraction

Don't classify every frame — detect which frames represent actual UI changes.

ScreenLLM (WWW 2025) computes **second-order pixel changes** between adjacent frames (variation in pixel *differences*, not raw pixel differences) to find transition points. This reduces thousands of frames to just the interesting ones.

**Relevance for us**: Before running VLM classification on the corpus, extract keyframes where the UI actually changed. Skip the 15 identical frames showing the same page.

- Source: [ScreenLLM (WWW 2025)](https://arxiv.org/abs/2503.20978)

### Pattern 4: Before/after reflection

Give the VLM two screenshots + the action taken between them → "did this action succeed?"

ScreenAgent (IJCAI 2024) uses a three-phase Plan-Act-Reflect loop. The Reflect phase receives before/after screenshots + the action and produces a structured assessment.

**Relevance for us**: Analyzing failures. "Here's the Meowfficer Fort screen before the click, here's what came after (black screen). What went wrong?"

- Source: [ScreenAgent (IJCAI 2024)](https://arxiv.org/abs/2402.07945)

### Pattern 5: Visual trace overlays

TraceVLA (ICLR 2025) encodes temporal history as a visual overlay on the current frame. Using point tracking (Co-Tracker), it draws colored trajectory lines showing where actions occurred across N=6 frames. The model receives just 2 images: the clean current frame + the annotated frame with traces.

**Relevance for us**: Instead of sending 6 screenshots, overlay the click positions from ALAS logs onto a single composite image. The VLM sees the navigation path visually.

- Source: [TraceVLA (ICLR 2025)](https://arxiv.org/abs/2412.10345)

### Pattern 6: Trajectory decomposition into graph triples

AppAgentX (March 2025) takes trajectories and decomposes them into (source-page, action, target-page) triples using an LLM. Stores results in a graph database (Neo4j). Merges duplicate pages automatically.

**Relevance for us**: This is exactly how we'd build graph.json from observations. Feed the VLM a chunk of the combined timeline → it outputs structured triples → we accumulate them into the state graph.

- Source: [AppAgentX (March 2025)](https://arxiv.org/abs/2503.02268)

## State machine inference from traces

### Formal automata learning (RPNI)

Classical algorithm: given positive and negative trace examples, build a minimal DFA. Works from page-ID sequences without needing screenshots. Production implementation: LearnLib (Java, v0.18.0). Python alternative: `alergia` package.

- Source: [RPNI tutorial](http://rahul.gopinath.org/post/2025/10/24/rpni-learning-regular-languages/)
- Source: [LearnLib](https://learnlib.de/)

### BFS exploration (DroidBot/Mobile3M style)

Systematically drive through all reachable pages, record transitions. Mobile3M (Sep 2024) built 49 directed graphs using BFS, producing 20M actions and 3M screenshots.

- Source: [Mobile3M (Sep 2024)](https://arxiv.org/abs/2409.14818)

### World models (MobileDreamer)

Train a model to predict what the UI will look like after an action. MobileDreamer (Jan 2026) uses structured text (OCR-extracted element descriptions) as state representation. Trained on 110k samples.

- Source: [MobileDreamer (Jan 2026)](https://arxiv.org/abs/2601.04035)

## Structured output from VLM

vLLM supports `guided_json` with Pydantic schemas on vision models. Use `enable_thinking=False` for classification calls. Requires vLLM >= 0.9.1 (0.9.0 had a bug with Qwen3 + structured output).

```python
from pydantic import BaseModel

class PageDetection(BaseModel):
    page_id: str
    confidence: float
    detected_elements: list[str]

response = client.chat.completions.create(
    model="QuantTrio/Qwen3.5-9B-AWQ",
    messages=[...],
    extra_body={
        "guided_json": PageDetection.model_json_schema(),
        "chat_template_kwargs": {"enable_thinking": False},
    },
)
```

## Token budget reference

| Scenario | Images | Image tokens | Text | Total | Fits 128k? |
|----------|--------|-------------|------|-------|------------|
| Single frame classify | 1 | 1,175 | ~200 | ~1,400 | Yes |
| 5-frame window + log chunk | 5 | 5,875 | ~1,000 | ~6,900 | Yes |
| 20-frame window + log | 20 | 23,500 | ~2,500 | ~26,000 | Yes |
| Full corpus scan (100 frames) | 100 | 117,500 | ~2,500 | ~120,000 | Barely |
| Half-res corpus (193 frames) | 193 | ~123,500 | ~2,500 | ~126,000 | Barely |

## Key references

- [Awesome-GUI-Agent (showlab)](https://github.com/showlab/Awesome-GUI-Agent) — comprehensive paper list
- [GUI-World dataset](https://gui-world.github.io/) — video benchmark for temporal GUI understanding
- [NVIDIA VLM Prompt Engineering Guide](https://developer.nvidia.com/blog/vision-language-model-prompt-engineering-guide-for-image-and-video-understanding/)
- [UFO (Microsoft)](https://arxiv.org/abs/2402.07939) — Windows GUI agent with memory and reflection
- [ICAL (NeurIPS 2024)](https://arxiv.org/abs/2406.14596) — trajectory abstraction for learning reusable knowledge
- [HyMEM (March 2025)](https://arxiv.org/abs/2603.10291) — hybrid graph memory from trajectories
