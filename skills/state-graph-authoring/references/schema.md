# State Graph Schema Reference

## Version

Current schema version: `1.0`

## Top-Level Structure

```json
{
  "version": "1.0",
  "metadata": {
    "system_name": "string",
    "scope": "string",
    "created": "ISO 8601 date",
    "explorer_dataset": "path to screenshots directory"
  },
  "states": { ... },
  "transitions": { ... }
}
```

## States

Each state is keyed by a unique identifier (snake_case):

```json
{
  "state_id": {
    "type": "normal | wait",
    "description": "Human-readable description",
    "anchors": [ ... ],
    "negative_anchors": [ ... ],
    "confidence_threshold": 0.85,
    "irreversible": false,
    "wait_state": { ... }
  }
}
```

### State Types

- **`normal`**: Standard state. Agent can take actions.
- **`wait`**: System is doing autonomous work. Agent should poll, not act.

### Anchors

An anchor is a cheap signal that confirms "you are in this state."

```json
{
  "type": "dom_element | text_match | pixel_color | screenshot_region | window_title | adb_focus",
  "cost": 1,
  "selector": "CSS selector (for dom_element)",
  "pattern": "regex pattern (for text_match, window_title, adb_focus)",
  "coordinates": [x, y],
  "color": [r, g, b],
  "bbox": [x1, y1, x2, y2],
  "hash": "perceptual hash string"
}
```

#### Anchor Types

| Type | Cost | Signal | Use When |
|------|------|--------|----------|
| `dom_element` | 1 | CSS selector exists in DOM | Web apps with stable selectors |
| `text_match` | 2 | Regex matches visible text | Text-heavy UIs |
| `window_title` | 1 | Window title matches pattern | Desktop apps |
| `adb_focus` | 1 | Android activity/window matches | Mobile apps via ADB |
| `pixel_color` | 2 | Pixel at coordinates matches color | Stable UI with known layout |
| `screenshot_region` | 3-5 | Perceptual hash of screen region | Visual-only identification |

### Negative Anchors

Same structure as anchors, but **if matched, this is NOT the state**. Useful for disambiguating similar-looking states.

### Wait State Configuration

Only for `type: "wait"` states:

```json
{
  "wait_state": {
    "expected_duration_ms": 45000,
    "duration_range_ms": [30000, 120000],
    "poll_interval_ms": 5000,
    "exit_signals": [
      {
        "type": "dom_element",
        "selector": ".result-screen",
        "cost": 1
      }
    ],
    "timeout_behavior": "escalate_to_vision | retry | abort"
  }
}
```

### Confidence Threshold

Per-state override for the confidence required before taking actions. Defaults:
- Normal states: `0.70`
- States before consequential actions: `0.85`
- Irreversible states: `0.99`

## Transitions

Each transition is keyed by a unique identifier:

```json
{
  "transition_id": {
    "from": "source_state_id",
    "to": "target_state_id",
    "event": "human-readable event name",
    "action": { ... },
    "cost": 1,
    "method": "deterministic | vision_required | deterministic_polling",
    "fragile": false,
    "fallback": { ... }
  }
}
```

### Action Types

```json
// Deterministic DOM click
{"type": "dom_click", "selector": "button#submit"}

// Deterministic click by index
{"type": "dom_click_by_index", "selector": ".list-item", "index": 0}

// URL navigation
{"type": "navigate", "url": "/settings"}

// Keyboard shortcut
{"type": "keyboard", "keys": "Escape"}

// ADB tap at coordinates
{"type": "adb_tap", "coordinates": [450, 800]}

// System gesture
{"type": "system_gesture", "gesture": "back | home | recent"}

// Poll until signal
{"type": "poll_until_signal", "signal": "text_match:Victory|Defeat", "interval_ms": 5000}

// Vision-required (no deterministic alternative)
{"type": "vision_required", "description": "Find and tap the target element"}

// Pending (not yet determined)
{"type": "pending", "description": "Needs investigation during optimization"}
```

### Cost Scale

| Cost | Meaning | Example |
|------|---------|---------|
| 1 | Nearly free, instant | DOM click, system gesture |
| 2 | Cheap, minor overhead | Text search, index-based click |
| 3-5 | Moderate, some processing | Region screenshot, hash comparison |
| 10-20 | Noticeable, small vision | Targeted screenshot + OCR |
| 50+ | Expensive, full vision | Full screenshot + LLM reasoning |

### Fragile Transitions

Mark with `fragile: true` when the action might break (brittle selectors, coordinate-dependent clicks):

```json
{
  "fragile": true,
  "fragility_reason": "DOM selector may change with app update",
  "fallback": {
    "action": {"type": "vision_required", "description": "Fallback to vision"},
    "cost": 50
  }
}
```

## Validation

Use the schema validator to check graph integrity:

```bash
python plugin/scripts/schema_validator.py --graph graph.json
```

Checks:
- All anchor types are valid
- All costs are positive numbers
- Confidence thresholds are between 0 and 1
- Wait states have exit signals
- All transition source/destination states exist in the graph
- All action types are recognized
