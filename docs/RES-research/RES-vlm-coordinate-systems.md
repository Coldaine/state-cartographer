# RES: VLM Coordinate Systems & Grounding for Automation

> Research date: 2026-03-28
> Status: reference document — informs `ground_element` task contract and transport layer

## Problem Statement

Different VLMs report element locations using incompatible coordinate systems.
To translate a model's "click here" into an ADB tap, the runtime must:

1. Know what coordinate space the model outputs.
2. Know the resolution of the image that was sent to the model.
3. Map from model-space → screenshot-space → device-space.

This document catalogs the coordinate conventions of models relevant to this project, then proposes a normalization strategy.

---

## Model Coordinate Catalog

### Gemini (2.5 Flash / Pro)

| Property | Value |
|---|---|
| Format | `box_2d`: `[y_min, x_min, y_max, x_max]` |
| Axis order | **Y before X** (easy mistake) |
| Range | 0–1000 (normalized, both axes) |
| Origin | top-left corner |
| Point tap | center of box: `((x_min+x_max)/2, (y_min+y_max)/2)` after axis swap |

**Conversion to pixel coordinates:**

```python
# Gemini → pixel
scale_x = image_width  / 1000
scale_y = image_height / 1000
px_x = x_norm * scale_x
px_y = y_norm * scale_y
```

**Key gotcha:** The `[y, x, y, x]` ordering is the opposite of most CV conventions (`[x, y, x, y]`). If you forget to swap, taps land in the wrong place on non-square images.

Gemini also supports segmentation masks with the same `box_2d` format plus base64-encoded PNG probability maps.

**Source:** [Google AI docs — Image Understanding](https://ai.google.dev/gemini-api/docs/image-understanding)

---

### Qwen2-VL (7B)

| Property | Value |
|---|---|
| Format | `<\|box_start\|>(x1,y1),(x2,y2)<\|box_end\|>` |
| Axis order | X before Y (standard) |
| Range | 0–999 (normalized to 1000-grid) |
| Origin | top-left corner |

Qwen2-VL uses special tokens to delimit bounding boxes. Coordinates are normalized to a [0, 1000) range.

**Conversion:**

```python
# Qwen2-VL → pixel
px_x = x_norm / 1000 * image_width
px_y = y_norm / 1000 * image_height
```

---

### Qwen2.5-VL (7B / 72B)

| Property | Value |
|---|---|
| Format | `<\|box_start\|>(x1,y1),(x2,y2)<\|box_end\|>` |
| Axis order | X before Y |
| Range | **Actual pixel coords of the resized image** |
| Origin | top-left corner |

**Critical change from Qwen2-VL:** Qwen2.5-VL outputs coordinates in the *resized input image* pixel space, NOT normalized 0–1000. You must know the model's internal resize dimensions (via `smart_resize`) to convert back to original image coordinates.

**Conversion:**

```python
# Qwen2.5-VL → original pixel
px_x = model_x / resized_width  * original_width
px_y = model_y / resized_height * original_height
```

The resized dimensions depend on `min_pixels`, `max_pixels`, and the patch size (28). Use `smart_resize()` from the Qwen2.5-VL processor to compute these deterministically.

**Source:** [Qwen GitHub issues #866, #1616](https://github.com/QwenLM/Qwen3-VL/issues/866)

---

### Qwen3-VL

| Property | Value |
|---|---|
| Format | `<\|box_start\|>(x1,y1),(x2,y2)<\|box_end\|>` |
| Axis order | X before Y |
| Range | 0–1000 (normalized, return of the Qwen2-VL convention) |
| Origin | top-left corner |

Qwen3-VL reverts to the 0–1000 normalized format. Same conversion as Qwen2-VL.

---

### Claude (Sonnet 4 / Opus 4 — Computer Use)

| Property | Value |
|---|---|
| Format | Absolute pixel coordinates `(x, y)` |
| Axis order | X before Y |
| Range | Pixel coordinates matching the screenshot resolution |
| Origin | top-left corner |
| Mechanism | "Pixel counting" from screen edges |

Claude's computer-use mode does NOT use bounding boxes or normalized coordinates. It expresses actions as raw pixel coordinates. The model counts pixels from reference points (edges, known elements) to produce tap locations.

**Key requirement:** The screenshot resolution sent to Claude IS the coordinate space. If you downscale screenshots before sending, taps must be scaled back up.

**Conversion:**

```python
# Claude → device pixel
device_x = claude_x * (device_width  / screenshot_width)
device_y = claude_y * (device_height / screenshot_height)
```

When used in `browser-use` or similar harnesses, there's a known multi-resolution mismatch between:
1. Actual viewport size
2. LLM screenshot size (e.g. 1400×850 for Sonnet)
3. Internal coordinate dispatch space

**Source:** [Anthropic docs — Vision](https://platform.claude.com/docs/en/build-with-claude/vision)

---

### SeeClick (Qwen-VL backbone, 9.6B)

| Property | Value |
|---|---|
| Format | `click(x, y)` |
| Axis order | X before Y |
| Range | [0, 1] (ratio of image dimensions) |
| Origin | top-left corner |

SeeClick is a GUI-grounding specialist. It outputs normalized 0–1 ratios, making conversion simple:

```python
px_x = x_ratio * image_width
px_y = y_ratio * image_height
```

Achieves 53.4% average on ScreenSpot (vs GPT-4V at 16.2%).

---

### UI-TARS (7B / 72B)

| Property | Value |
|---|---|
| Format | `(x, y)` for clicks; `(x1,y1),(x2,y2)` for boxes |
| Axis order | X before Y |
| Range | 0–1000 (normalized) |
| Origin | top-left corner |

UI-TARS is specifically designed for GUI automation. It uses the same 0–1000 normalized space as Gemini and Qwen2-VL. Conversion is identical.

UI-TARS achieves SOTA on ScreenSpot Pro and is the strongest open model for GUI grounding as of early 2026.

**Source:** [UI-TARS paper](https://arxiv.org/html/2501.12326v1), [seed-tars.com](https://seed-tars.com/1/)

---

### CogAgent (18B)

| Property | Value |
|---|---|
| Format | Bounding box with `box` attribute in grounded operations |
| Axis order | X before Y |
| Range | Pixel coordinates |
| Origin | top-left corner |

CogAgent outputs bounding boxes as pixel coordinates within the input image resolution. It wraps these in structured operation descriptions.

---

### Kimi-VL / Kimi K2.5 (MoE, 2.8B active)

| Property | Value |
|---|---|
| Format | Not explicitly documented — uses pixel-level grounding |
| Grounding scores | 92.0% ScreenSpot-V2, 34.5% ScreenSpot-Pro |
| Architecture | MoonViT-3D encoder → MLP projector → MoE LLM |

Kimi-VL demonstrates strong grounding but the public API does not yet expose a documented coordinate format for bounding boxes. It processes images at native resolution via patch packing (NaViT-style).

Kimi K2.5 adds video understanding and an "Agent Swarm" system for parallel sub-agent coordination.

**Source:** [Kimi-VL Technical Report](https://arxiv.org/html/2504.07491v1), [Kimi K2.5 paper](https://arxiv.org/html/2602.02276v1)

---

## Summary: Coordinate Space Quick Reference

| Model | Axis Order | Range | Type |
|---|---|---|---|
| Gemini 2.5 | **Y, X** | 0–1000 | normalized |
| Qwen2-VL | X, Y | 0–999 | normalized |
| Qwen2.5-VL | X, Y | resized px | absolute (resized) |
| Qwen3-VL | X, Y | 0–1000 | normalized |
| Claude (CU) | X, Y | screenshot px | absolute |
| SeeClick | X, Y | 0–1 | ratio |
| UI-TARS | X, Y | 0–1000 | normalized |
| CogAgent | X, Y | image px | absolute |
| Kimi-VL | — | (undocumented) | — |

---

## Proposed Normalization Layer

### Internal canonical form

All coordinates entering the runtime should be converted to:

```
(x_norm, y_norm)  ∈ [0.0, 1.0]  ×  [0.0, 1.0]
```

- Origin: top-left
- Axis order: X, Y (width fraction, height fraction)
- A point tap is `(x, y)`. A box is `(x1, y1, x2, y2)`.

### Why [0, 1] and not [0, 1000]?

- Resolution-independent: works across any screenshot size
- No rounding artifacts from integer grids
- Easy to convert to any device coordinate on output
- Compatible with the SeeClick convention and common CV libraries

### Adapter functions (per model)

```python
def from_gemini(box_2d: list[int], img_w: int, img_h: int) -> tuple:
    """Gemini box_2d = [y_min, x_min, y_max, x_max], normalized 0-1000."""
    y_min, x_min, y_max, x_max = box_2d
    return (x_min / 1000, y_min / 1000, x_max / 1000, y_max / 1000)

def from_qwen2vl(coords: tuple, img_w: int, img_h: int) -> tuple:
    """Qwen2-VL coords = (x1, y1, x2, y2), normalized 0-999."""
    x1, y1, x2, y2 = coords
    return (x1 / 1000, y1 / 1000, x2 / 1000, y2 / 1000)

def from_qwen25vl(coords: tuple, resized_w: int, resized_h: int) -> tuple:
    """Qwen2.5-VL coords = (x1, y1, x2, y2), pixels in resized image."""
    x1, y1, x2, y2 = coords
    return (x1 / resized_w, y1 / resized_h, x2 / resized_w, y2 / resized_h)

def from_claude(x: int, y: int, screenshot_w: int, screenshot_h: int) -> tuple:
    """Claude pixel coordinate → normalized point."""
    return (x / screenshot_w, y / screenshot_h)

def from_seeclick(x: float, y: float) -> tuple:
    """SeeClick already in [0, 1] — passthrough."""
    return (x, y)

def from_uitars(coords: tuple) -> tuple:
    """UI-TARS coords = (x, y) or (x1,y1,x2,y2), normalized 0-1000."""
    return tuple(c / 1000 for c in coords)
```

### From canonical → device tap

```python
def to_device_tap(x_norm: float, y_norm: float,
                  device_w: int, device_h: int) -> tuple[int, int]:
    """Convert [0,1] normalized point to device ADB coordinates."""
    return (round(x_norm * device_w), round(y_norm * device_h))
```

---

## Screenshot Metadata Requirements

For coordinate translation to work, every screenshot entering the VLM pipeline must carry:

| Field | Purpose |
|---|---|
| `capture_width` | Pixel width of the raw capture |
| `capture_height` | Pixel height of the raw capture |
| `device_width` | Device logical resolution width (for ADB tap) |
| `device_height` | Device logical resolution height |
| `sent_width` | Width of image actually sent to the model |
| `sent_height` | Height of image actually sent to the model |
| `scale_factor` | `device_width / sent_width` (precomputed convenience) |
| `model_id` | Which model will interpret this image |
| `timestamp` | When the screenshot was taken |

If the image is resized before sending (common for token savings), the `sent_*` fields differ from `capture_*` and the adapter must use `sent_*` for conversion.

For Qwen2.5-VL specifically, the `resized_width` / `resized_height` from `smart_resize()` must also be recorded, as the model's internal resize may differ from our pre-send resize.

---

## Grounding Accuracy Benchmarks (ScreenSpot)

These numbers inform model selection for `ground_element` tasks:

| Model | Mobile Text | Mobile Icon | Desktop Text | Desktop Icon | Web Text | Web Icon | Avg |
|---|---|---|---|---|---|---|---|
| GPT-4V | 22.6 | 24.5 | 20.2 | 11.8 | 9.2 | 8.8 | **16.2** |
| CogAgent | 67.0 | 24.0 | 74.2 | 20.0 | 70.4 | 28.6 | **47.4** |
| SeeClick | 78.0 | 52.0 | 72.2 | 30.0 | 55.7 | 32.5 | **53.4** |
| R-VLM (SeeClick+) | 85.0 | 61.1 | 81.4 | 52.8 | 66.5 | 51.4 | **66.3** |
| UI-TARS-72B | — | — | — | — | — | — | **SOTA on ScreenSpot-Pro** |
| Kimi-VL | — | — | — | — | — | — | **92.0 SSv2 / 34.5 SS-Pro** |

Key takeaway: General-purpose VLMs (GPT-4V, Claude) are weak at precise coordinate grounding. Purpose-built GUI agents (UI-TARS, SeeClick, Kimi-VL) are dramatically better. For this project's `ground_element` task, a grounding-specialized model should be the primary, with a general VLM as adjudicator.

---

## Common Pitfalls

1. **Gemini Y-before-X:** The most frequent error. Always unpack `[y, x, y, x]`, not `[x, y, x, y]`.

2. **Qwen2.5-VL resized-pixel trap:** Coordinates are in the model's internal resized space, not the original image. Must track `smart_resize()` output.

3. **DPI/scaling mismatch:** Android emulators may report a logical resolution different from the actual screencap resolution. ADB `wm size` vs `screencap` dimensions can diverge, especially on Vulkan-rendered emulators.

4. **PDF vs image in Gemini:** Sending a PDF page loses spatial context. Always send as image for grounding tasks.

5. **Claude screenshot downscale:** If you reduce screenshot resolution to save tokens, Claude's pixel coordinates must be scaled back up before dispatching the tap.

6. **Model output instability:** Some models (Qwen2.5-VL without careful prompt engineering) may inconsistently output normalized vs pixel coordinates. The prompt must explicitly request the expected format.

---

## Implications for This Project

### Transport layer (`state_cartographer/transport/`)

The `pilot.py` facade should accept normalized `(x, y)` in [0, 1] and handle the final `→ device pixel` conversion internally. Callers should never deal with raw pixel math.

### VLM task contracts (`docs/vlm/VLM-task-contracts.md`)

The `ground_element` contract currently specifies `bbox` as `[x1, y1, x2, y2]` without stating the coordinate space. It should be updated to require normalized [0, 1] output, or to require explicit metadata about the space used.

### Model profiles (`docs/vlm/VLM-model-profiles.md`)

Each profile should declare:
- `coordinate_format`: one of `norm_1000_yx`, `norm_1000_xy`, `resized_px`, `screenshot_px`, `ratio_01`
- `coordinate_adapter`: function name from the adapter catalog above

### Screenshot pipeline

Every screenshot path (ADB screencap → resize → send to model) must track and preserve the metadata listed in the "Screenshot Metadata Requirements" section.

---

## References

- [Gemini Image Understanding docs](https://ai.google.dev/gemini-api/docs/image-understanding)
- [Qwen2.5-VL grounding issues](https://github.com/QwenLM/Qwen3-VL/issues/866)
- [UI-TARS paper](https://arxiv.org/html/2501.12326v1)
- [SeeClick paper](https://openreview.net/pdf/4b5f397355df51294432bb9e8d8641fe7f3426c1.pdf)
- [Kimi-VL Technical Report](https://arxiv.org/html/2504.07491v1)
- [Claude Vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- [R-VLM paper](https://arxiv.org/html/2507.05673v1)
- [ScreenAgent / IJCAI-24](https://www.ijcai.org/proceedings/2024/0711.pdf)
