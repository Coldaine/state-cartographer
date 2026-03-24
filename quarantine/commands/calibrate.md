---
name: Calibrate
description: Learn anchor values from real screenshots and write them to graph.json
type: command
usage: /calibrate
---

# /calibrate — Anchor Calibrator

Learn real pixel colors and perceptual hashes from screenshots of known states and write them back to `graph.json`. This is the **first-mile tool**: it turns a graph with blank anchor templates into one with real, learned values.

## What it does

| Anchor type | What gets learned |
|-------------|-------------------|
| `pixel_color` | Samples the screenshot at `(x, y)` → writes to `expected_rgb` |
| `screenshot_region` | Crops the region → computes perceptual hash → writes to `hash` |
| `text_match`, `dom_element` | Not modified (no visual learning applies) |

## Usage

```bash
# Calibrate one state from a screenshot of that state
python scripts/calibrate.py --graph graph.json --screenshot main_menu.png --state main_menu

# Preview changes without writing (dry-run)
python scripts/calibrate.py --graph graph.json --screenshot login.png --state login --dry-run

# Calibrate all states from a single screenshot
# (only useful if all states appear on the same screen)
python scripts/calibrate.py --graph graph.json --screenshot screen.png --state all
```

## Typical workflow

1. Build your `graph.json` with state/transition structure and **anchor shapes** (coordinates for `pixel_color`, regions for `screenshot_region`). Leave `expected_rgb` and `hash` blank.
2. Navigate the real system to each state and take a screenshot.
3. For each state, run `calibrate.py` to fill in the anchor values.
4. Validate with `schema_validator.py` to confirm the graph is well-formed.
5. Run `locate.py` against new screenshots to verify the classifier works.

## Requirements

```bash
# Pixel color sampling only
uv sync --extra vision

# Perceptual hash (screenshot_region) also requires imagehash:
uv sync --extra vision
```

## Output (success)

```json
{
  "calibrated": 1,
  "states": ["main_menu"],
  "warnings": [],
  "written_to": "graph.json"
}
```

Warnings are emitted when:
- An anchor value **changed** (the old value is printed so you can verify intentionally)
- A pixel coordinate is outside image bounds
- `imagehash` is not installed for `screenshot_region`

## Output (dry-run)

Returns the **full updated graph** as JSON without modifying the file on disk. Useful for inspection before committing to changes.
