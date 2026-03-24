# Data Collection & Ship Census Design

> Historical note: moved from `docs/execution/EXE-data-collection.md` and previously framed as part of the `EXE` domain.


> This document defines the "second scheduler" — a data-gathering system that
> inventories every ship, their stats, equipment, and skill levels by paging
> through game screens and recording everything via OCR and screenshots.

## Why a Second Scheduler?

The primary scheduler (Layer 4) runs **action tasks**: collect commissions,
dispatch research, feed dorm. These are time-driven and fire-and-forget.

Data collection is fundamentally different:

- **Pagination-driven**: page through 500+ ships, one screenful at a time
- **Read-heavy, write-light**: 95% screenshot + OCR, 5% taps to page/navigate
- **One-shot or periodic**: run a full census once a week, not every 60 minutes
- **Produces a database**: output is a structured ship roster, not a resource delta
- **Interruptible**: can stop mid-census and resume later

The primary scheduler doesn't handle pagination workflows well. It needs a
**data collection scheduler** that treats "gather information" as a first-class
operation type.

## Architecture

```
┌──────────────────────────────────────────────────┐
│              Data Collection Scheduler            │
│  (scripts/data_collector.py)                      │
│                                                   │
│  Jobs:                                           │
│  - ship_census     (dock → page all ships)       │
│  - ship_detail     (single ship stats/equip)     │
│  - formation_audit (all fleet formations)        │
│  - dorm_status     (dorm comfort + ships)        │
│  - resource_scan   (all resource screens)        │
│  - guild_roster    (guild member list)           │
│  - opsi_map        (OpSi zone status)            │
└───────────────┬──────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────┐
│              Data Store                           │
│  (data/census/)                                   │
│                                                   │
│  ships.json      — master ship roster            │
│  equipment.json  — equipment inventory           │
│  formations.json — fleet compositions            │
│  resources.json  — resource snapshots            │
│  screenshots/    — labeled screenshots           │
└──────────────────────────────────────────────────┘
```

## Data Collection Jobs

### Job 1: Ship Census (Dock Paging)

**Goal:** Build a complete roster of all ships in the dock.

**Entry:** `page_dock` (with sort/filter applied)

**Procedure:**
1. Navigate to dock
2. Set sort order (by level, descending)
3. Set filter (all types, all rarities)
4. Read ship count header (e.g., "312/400")
5. For each page (7×2 = 14 ships per page):
   a. Screenshot the grid
   b. For each ship card in the grid:
      - Read rarity (color sampling: gray/blue/purple/gold)
      - Read level (OCR on level text region)
      - Read name (OCR on name region, or skip if too small)
      - Read emotion indicator (icon color)
      - Record grid position for detail tap
   c. After processing grid, swipe up to next page
   d. Detect end of list (last page has fewer cards or no scroll)
6. Save `data/census/ships.json` with full roster

**Grid Layout (per ALAS):**
```
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 0,0 │ 1,0 │ 2,0 │ 3,0 │ 4,0 │ 5,0 │ 6,0 │  Row 0
├─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ 0,1 │ 1,1 │ 2,1 │ 3,1 │ 4,1 │ 5,1 │ 6,1 │  Row 1
└─────┴─────┴─────┴─────┴─────┴─────┴─────┘
14 ships × N pages = full dock
```

**Ship Card Data Model:**
```json
{
  "id": "ship_001",
  "name": "Enterprise",
  "rarity": "SSR",
  "level": 125,
  "emotion": "happy",
  "retrofit": false,
  "oath": true,
  "fleet_assigned": 1,
  "dock_position": 42,
  "last_seen": "2026-03-16T12:00:00Z",
  "screenshot": "data/census/screenshots/ship_001.png"
}
```

**OCR Regions (relative to ship card):**
| Region | Content | Method |
|--------|---------|--------|
| Top-left corner | Rarity frame color | Color sampling (±15 RGB) |
| Bottom-center | Level number | OCR (digits only) |
| Top-center | Name text | OCR (alpha + locale) |
| Top-right | Emotion icon | Template match or color |
| Border glow | Oath ring indicator | Gold border detection |
| Fleet badge | Fleet assignment | Number OCR or template |

### Job 2: Ship Detail Census

**Goal:** For each ship, capture full stats, equipment, and skills.

**Procedure:** For each ship in roster (or a filtered subset):
1. Tap ship card in dock to open detail view
2. **Stats page:**
   a. Screenshot stats panel
   b. OCR: HP, Firepower, Torpedo, Aviation, Anti-Air, Reload, Evasion, Speed, Luck, Accuracy
   c. OCR: Affinity level
   d. Record all stats
3. **Equipment page:**
   a. Tap equipment tab
   b. For each of 3-5 equipment slots:
      - Screenshot equipment icon
      - OCR: equipment name
      - OCR: enhancement level (+10, +13, etc.)
      - Template match: equipment rarity color
   c. Record all equipment
4. **Skill page:**
   a. Tap skill tab
   b. For each skill (1-4 skills per ship):
      - OCR: skill name
      - OCR: skill level (1-10)
      - Template match: skill type icon (red/blue/yellow)
   c. Record all skills
5. Close detail view (back button)
6. Move to next ship

**Ship Detail Data Model:**
```json
{
  "id": "ship_001",
  "name": "Enterprise",
  "stats": {
    "hp": 7432,
    "firepower": 0,
    "torpedo": 0,
    "aviation": 456,
    "anti_air": 312,
    "reload": 156,
    "evasion": 78,
    "speed": 33,
    "luck": 15,
    "accuracy": 134,
    "affinity": 200
  },
  "equipment": [
    {
      "slot": 1,
      "name": "F4U Corsair (VF-17 Squadron)",
      "enhancement": 13,
      "rarity": "rainbow"
    },
    {
      "slot": 2,
      "name": "SB2C Helldiver",
      "enhancement": 10,
      "rarity": "purple"
    }
  ],
  "skills": [
    {
      "name": "Lucky E",
      "level": 10,
      "type": "offense"
    },
    {
      "name": "Assault Orders",
      "level": 10,
      "type": "support"
    }
  ],
  "last_detailed": "2026-03-16T12:05:00Z"
}
```

### Job 3: Formation Audit

**Goal:** Record all fleet compositions across all fleet slots.

**Entry:** `page_fleet` / `page_formation`

**Procedure:**
1. Navigate to formation screen
2. For each fleet (1-6+):
   a. Select fleet tab
   b. Read fleet name
   c. For each slot (vanguard 3 + main 3 = 6 per fleet):
      - Read ship name or icon
      - Record position (main/vanguard, slot number)
   d. Screenshot the formation
3. Save `data/census/formations.json`

### Job 4: Resource Scan

**Goal:** Capture all resource values from resource screens.

**Entry:** Various screens (main, shop, depot)

**Procedure:**
1. Read from `page_main` header: Oil, Coins, Gems
2. Navigate to depot screen: all items with counts
3. Navigate to shop: current prices vs budgets

**Output:** `data/census/resources.json` with timestamped snapshot

### Job 5: Dorm Status Audit

**Goal:** Record dorm state — comfort, assigned ships, food level, mood.

**Entry:** `page_dorm`

**Procedure:**
1. Navigate to dorm
2. Read comfort level
3. Read food fill percentage
4. Identify assigned ships (6 slots across floors)
5. Read mood for each ship
6. Screenshot each floor
7. Save `data/census/dorm_status.json`

### Job 6: Guild Roster

**Goal:** Record all guild members and their contributions.

**Entry:** `page_guild` → Members tab

**Procedure:**
1. Navigate to guild member list
2. Page through all members
3. For each member: read name, level, last active, contribution
4. Save `data/census/guild_roster.json`

### Job 7: OpSi Map Status

**Goal:** Record OpSi zone states — explored, completed, boss status.

**Entry:** OpSi world map

**Procedure:**
1. Navigate to OpSi map
2. For each visible zone: read coordinates, status, hazard level
3. Record explored vs unexplored zones
4. Record boss/stronghold locations
5. Save `data/census/opsi_map.json`

---

## Pagination Engine

All census jobs share the same pagination pattern:

```python
def paginate_screen(
    screenshot_fn,     # → PIL.Image
    extract_fn,        # Image → list[dict] (items on this page)  
    scroll_fn,         # → None (scroll to next page)
    is_last_page_fn,   # list[dict] → bool
    max_pages=100,
) -> list[dict]:
    """Generic pagination: screenshot, extract, scroll, repeat."""
    all_items = []
    for page_num in range(max_pages):
        img = screenshot_fn()
        items = extract_fn(img, page_num)
        all_items.extend(items)
        if is_last_page_fn(items):
            break
        scroll_fn()
        time.sleep(0.5)  # settle after scroll
    return all_items
```

**End-of-list detection:**
- Ship count from header matches accumulated count
- Last page has fewer than 14 cards
- Consecutive pages return identical data (scroll didn't move)
- Pixel check at bottom of scroll area

---

## Census Scheduler Integration

The data collection scheduler is a separate scheduling loop from the primary
task scheduler. It runs at lower priority and can be preempted by urgent tasks.

```python
# In scripts/data_collector.py

CENSUS_JOBS = {
    "ship_census": {
        "schedule": {"type": "interval", "hours": 168},  # weekly
        "entry_state": "page_dock",
        "interruptible": True,
        "resume_from": "last_page_index"
    },
    "ship_detail": {
        "schedule": {"type": "manual"},  # on-demand
        "entry_state": "page_dock",  
        "interruptible": True,
        "resume_from": "last_ship_index"
    },
    "formation_audit": {
        "schedule": {"type": "interval", "hours": 24},
        "entry_state": "page_fleet",
        "interruptible": False  # quick enough to complete
    },
    "resource_scan": {
        "schedule": {"type": "interval", "minutes": 30},
        "entry_state": "page_main",
        "interruptible": False
    },
    "dorm_status": {
        "schedule": {"type": "interval", "hours": 8},
        "entry_state": "page_dorm",
        "interruptible": False
    }
}
```

**Preemption logic:**
1. Primary scheduler has a task ready → pause census
2. Save census progress (page index, items collected so far)
3. Run primary task
4. Resume census from saved checkpoint

---

## Recording Integration

Every screenshot taken during data collection is saved with metadata:

```json
{
  "job": "ship_census",
  "page": 12,
  "timestamp": "2026-03-16T12:03:45Z",
  "screenshot": "data/census/screenshots/dock_page_012.png",
  "items_extracted": 14,
  "sort_order": "level_desc",
  "filter": "all"
}
```

This uses the existing `execution_event_log.py` NDJSON system with
`event_type: "observation"` and `semantic_action: "census_page"`.

---

## Where This Lives in the Architecture

```
Layer 5: Agent Supervision
Layer 4.5: Data Collection Scheduler  ← NEW
Layer 4: Task Scheduler + Daemon Loop
Layer 3: Task Definitions + Resource Model
Layer 2: Runtime Navigation Tools
Layer 1: Schema + Graph
Layer 0: Libraries
```

Layer 4.5 sits between the task scheduler and agent supervision because:
- It uses the same navigation tools as the task scheduler (Layer 2)
- It produces data that feeds the agent's decision-making (Layer 5)
- It needs to yield to the task scheduler for urgent work
- It has its own scheduling and resumption logic
