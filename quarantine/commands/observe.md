---
name: Observe Screenshot
description: Extract structured observations from a screenshot for use by the state classifier. Samples pixel colors at anchor coordinates and records the screenshot path for visual hash matching.
type: command
usage: /observe
---

# Observe Screenshot

Build an observations dict from a screenshot file, ready to feed into `/locate`.

## When to Use

Use this when you have a screenshot of the current system state and need observations to run state classification. It bridges the gap between "I have a PNG" and "I can call locate.py."

## Instructions

1. Capture a screenshot of the current system state.
2. Run the observation extractor, pointing it at the graph so it knows which pixel coordinates to sample:
   ```
   python scripts/observe.py --screenshot current.png --graph graph.json --output obs.json
   ```
3. Optionally add text content or DOM elements to `obs.json` manually if you have them.
4. Pass the result to the state classifier:
   ```
   python scripts/locate.py --graph graph.json --session session.json --observations obs.json
   ```

## Output Format

```json
{
  "screenshot": "/absolute/path/to/current.png",
  "pixels": {
    "100,200": [255, 128, 0],
    "50,30": [0, 0, 0]
  },
  "text_content": null,
  "dom_elements": []
}
```

- `screenshot`: Absolute path, used by `screenshot_region` anchors in locate.py
- `pixels`: Sampled pixel colors at `pixel_color` anchor coordinates
- `text_content`: Fill this in manually or via OCR if your anchors include `text_match`
- `dom_elements`: Fill this in from browser DevTools if your anchors include `dom_element`

## Vision Extra Required

Pixel sampling requires Pillow. Install it with:
```
uv sync --extra vision
```

Without it, `observe.py` still runs and records the screenshot path — `screenshot_region` anchor evaluation will still work since locate.py opens the image directly. Only `pixel_color` anchor sampling is skipped.
