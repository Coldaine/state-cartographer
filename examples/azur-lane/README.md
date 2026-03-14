# Azur Lane — State Graph Example

State graph for the [Azur Lane](https://azurlane.yo-star.com/) mobile game running on
[MEMU](https://www.memuplay.com/) Android emulator, connected via ADB.

Coordinates derived from [AzurLaneAutoScript (ALAS)](https://github.com/Zuosizhu/Alas-with-Dashboard)
button definitions. Resolution: **1280 × 720 landscape** (the only resolution the game supports).

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| MEMU emulator | Running with Azur Lane installed and launched |
| ADB | On your PATH (`adb version` should work) |
| State Cartographer | Installed (`uv pip install -e ".[dev,vision]"`) |

Connect MEMU to ADB before using any commands:

```bash
adb connect 127.0.0.1:21503   # most MEMU versions
# or
adb connect 127.0.0.1:21513   # some newer MEMU versions
adb devices                    # verify — should show "device" state
```

---

## ⚠️ Calibration Required

All `expected_rgb` values in `graph.json` are `[0, 0, 0]` **placeholders**.
The graph will not produce correct state classifications until each anchor is
calibrated against a real in-game screenshot.

### Calibration Workflow

1. **Start MEMU and launch Azur Lane.** Navigate to the state you want to calibrate.

2. **Take a screenshot via adb_bridge:**
   ```bash
   python scripts/adb_bridge.py screenshot --serial 127.0.0.1:21503 --output screen.png
   ```

3. **Calibrate the anchor values for that state:**
   ```bash
   python scripts/calibrate.py \
       --graph examples/azur-lane/graph.json \
       --screenshot screen.png \
       --state page_main
   ```
   Repeat for every state in the graph (`page_dock`, `page_fleet`, `page_build`, …).

4. **Verify the graph validates cleanly:**
   ```bash
   python scripts/schema_validator.py examples/azur-lane/graph.json
   ```

---

## Live State Classification

Once calibrated, classify the current game state live:

```bash
python scripts/observe.py \
    --adb 127.0.0.1:21503 \
    --graph examples/azur-lane/graph.json \
    --output obs.json

python scripts/locate.py \
    --graph examples/azur-lane/graph.json \
    --observations obs.json
```

Or as a one-liner:

```bash
python scripts/observe.py --adb 127.0.0.1:21503 --graph examples/azur-lane/graph.json | \
    python scripts/locate.py --graph examples/azur-lane/graph.json --observations /dev/stdin
```

---

## Pathfinding

Navigate from the current state to a target:

```bash
python scripts/pathfind.py \
    --graph examples/azur-lane/graph.json \
    --from page_main \
    --to page_dock
```

Each transition's `action` object carries `{"type": "adb_tap", "x": ..., "y": ...}` —
feed these coordinates to `adb_bridge.py tap` to execute the navigation step:

```bash
python scripts/adb_bridge.py tap --serial 127.0.0.1:21503 --x 249 --y 691
```

---

## State Map

| State | Description | Detection anchor |
|-------|-------------|-----------------|
| `page_main` | Hub — fleet collection tiles visible | MAIN_GOTO_FLEET area (903, 391) |
| `page_dock` | Ship roster / collection | Dock nav tab highlighted (249, 691) |
| `page_fleet` | Fleet formation management | GOTO_MAIN present + page header (640, 80) |
| `page_build` | Ship construction | Build nav tab highlighted (1035, 699) |
| `page_guild` | Guild management | Guild nav tab highlighted (1193, 689) |
| `page_reward` | Daily missions / rewards | GOTO_MAIN present + page header (640, 80) |
| `page_campaign` | World map / campaign | GOTO_MAIN present + page header (640, 80) |

All non-main states are returned to `page_main` by tapping GOTO_MAIN at **(1229, 34)**
(top-right home button, present on every page except `page_main`).

---

## Extending the Graph

ALAS defines 40+ game pages. To add more states:

1. Add a state entry to `graph.json` using the `page_*` naming convention.
2. Look up the `check_button` area in ALAS's `module/ui/page.py` for anchor coordinates.
3. Calibrate with a real screenshot of that page.
4. Add transitions referencing known button coordinates.

The second `pixel_color` anchor for `page_fleet`, `page_reward`, and `page_campaign` 
currently points to the generic page header region `(640, 80)`. These share the same 
placeholder and **must be given distinct coordinates** after initial calibration — choose
a region unique to each page to avoid ambiguity.
