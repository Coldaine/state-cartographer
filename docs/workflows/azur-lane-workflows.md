# Azur Lane Automation Workflows

> Historical note: moved from `docs/execution/EXE-workflows.md` and previously filed under the `EXE` domain.

## Status Framing

This document is a workflow inventory and complexity map.

It does **not** mean every workflow below is currently implemented, trusted, or runnable. Unless a workflow is explicitly marked otherwise elsewhere, treat the entries here as design and planning knowledge.

## Current Interpretation

Use this file to answer:
- what workflows exist?
- what each workflow reads and decides on?
- what substates and failure modes make the workflow difficult?

Do not use this file alone as evidence that the repo can execute the workflow today.

See also:
- [todo.md](/mnt/d/_projects/MasterStateMachine/docs/todo.md)

## Workflow Categories

| Category | Workflows | Frequency | Current status |
|----------|-----------|-----------|----------------|
| Lifecycle | Restart, Login | On-demand / error recovery | design inventory |
| Rewards | Reward collect, Mail collect | Every 15-30 min | design inventory |
| Commissions | Collect + dispatch | Every 60 min | design inventory |
| Research | Collect + select project | Every 60-480 min | design inventory |
| Dorm | Feed ships, collect love/coins | Every 4-8 hours | design inventory |
| Private Quarters | Buy roses/cakes, interact | Daily | design inventory |
| Guild | Logistics, tech, operations | Daily | design inventory |
| Daily Missions | Daily Hard/Normal stages | Daily | design inventory |
| Exercise | PvP battles | 3x daily (reset windows) | design inventory |
| Meowfficer | Buy, fort chores, train, enhance | Daily + intervals | design inventory |
| Shops | Frequent shop, one-time shop | Daily / weekly | design inventory |
| Retire | Dock cleanup by rarity | When dock full | design inventory |
| Operations Siren | 10+ sub-workflows | Daily / weekly / monthly | design inventory |
| Data Collection | Ship census, stats, equipment | On-demand | design inventory |

---

## 1. Restart + Login

**Purpose:** Cold-start or recover the game from crash/disconnect.

**Entry state:** `unknown` or `app_closed`
**Target state:** `page_main` (main menu)

**Sequence:**
1. Launch `com.YoStarEN.AzurLane` via ADB
2. Wait for black loading screen → splash screen → login button
3. Tap login if prompted
4. Handle popup announcements (tap X to dismiss, may be multiple)
5. Handle update prompts (confirm update if needed)
6. Arrive at `page_main`

**Data read:** None (pure navigation)
**Data produced:** Login timestamp, server identifier

**Error patterns:**
- Black screen stuck (GameStuckError) → kill app, retry
- Too many login taps without progress (GameTooManyClickError) → full restart
- Maintenance notice → wait + retry
- "Request human takeover" → escalate

---

## 2. Reward Collection

**Purpose:** Collect completed task/mission rewards from the reward notification.

**Entry state:** `page_main` (notice icon visible)
**Sequence:**
1. Check for reward indicator on main screen (red dot / notification badge)
2. Tap rewards button
3. Collect all available rewards (mail, missions, achievements)
4. Return to `page_main`

**Data read:** Reward notification badge (pixel color check)
**Data produced:** Reward types collected, resource deltas

---

## 3. Commission Workflow

**Purpose:** Collect completed commissions, dispatch new ones.

**Entry state:** `page_commission`
**Navigation:** `page_main` → `page_campaign` → `page_commission`

**Sequence:**
1. Navigate to commission page
2. Check for completed commissions (green "Completed" status)
3. Tap each completed commission → collect rewards
4. Switch between Daily and Urgent tabs
5. For each available commission slot:
   a. Read commission name (OCR), duration, rewards
   b. Apply selection filter (regex matching against config preset)
   c. Select best available commission
   d. Dispatch selected commissions
6. Record timer for earliest completion
7. Return to `page_main`

**Data read (OCR regions):**
- Commission name text
- Duration text (HH:MM:SS)
- Reward icons + amounts
- Status color (RGB voting: white=available, green=completed, gray=running)
- Commission count per tab

**Decision logic:**
- Priority preset (e.g., "gem commissions first", "shortest duration", "night commissions")
- Filter by duration, rewards, or name regex
- Select up to 4 commissions (5 if daily_event active)

**Data produced:**
- Commission completion timestamps
- Dispatched commission names + expected completion times
- Resource gains from collection (oil, coins, cubes, gems)

**Timers set:** `commission_next_collect` = earliest dispatched commission completion

---

## 4. Research Workflow

**Purpose:** Collect completed research, select and start new project.

**Entry state:** `page_research`
**Navigation:** `page_main` → `page_campaign` → `page_research` (or via main menu shortcut)

**Sequence:**
1. Navigate to research page
2. Check if current research is complete (green status indicator)
3. If complete: tap to collect research rewards
4. View 5 available research project slots
5. For each project, read:
   a. Project name + series (OCR with Roman numeral detection)
   b. Duration
   c. Resource cost (coins/cubes)
   d. Whether project is a priority type
6. Apply selection logic (series preference, resource budget, queue order)
7. Start selected project
8. Return to `page_main`

**Data read (OCR + CV):**
- Research project names (OCR)
- Series indicator: Roman numerals I-VI detected via Sobel edge gradient angles
- Duration (OCR)
- Resource cost icons + amounts (OCR)
- Completion status (green pixel color check)
- Research queue position

**Decision logic:**
- Series preference configured per user (prefer Series V, avoid Series I)
- Resource budget check (enough coins/cubes?)
- Duration preference (short for active play, long for overnight)
- Queue logic: if queue_enabled, can stack projects
- Reset option: if no good projects, reset the pool

**Data produced:**
- Research completion timestamp
- Selected project name, series, duration
- Resource expenditure

**Timers set:** `research_complete` = start_time + project_duration

---

## 5. Dorm Workflow

**Purpose:** Feed ships in dorm, collect love/coin rewards, manage comfort.

**Entry state:** `page_dorm`
**Navigation:** `page_main` → `page_dorm`

**Sequence:**
1. Navigate to dorm
2. Collect reward items:
   a. Template-match love icons (heart shapes) — up to 6
   b. Template-match coin icons — up to 6
   c. Tap each matched icon to collect
3. Check food level:
   a. Read food fill bar (custom OCR: orange pixels vs gray pixels)
   b. If below threshold:
      - Open food menu
      - Select appropriate food item (1K-20K exp options)
      - Long-tap to fill (device-specific: minitouch/MaaTouch/uiautomator2)
      - Close food menu
4. Optionally buy furniture if time-limited sale active:
   a. Navigate to furniture shop
   b. Read prices (OCR)
   c. Purchase if within budget
5. Return to `page_main`

**Data read:**
- Love/coin icon positions (template matching with mask)
- Food fill percentage (orange+gray pixel ratio)
- Furniture prices (OCR)
- Ship mood indicators (visible on dorm floor)

**Decision logic:**
- Feed threshold: configurable minimum food level
- Food selection: pick cheapest food that fills above threshold
- Furniture buy: only time-limited items, only if coins > threshold

**Data produced:**
- Love/coin collected counts
- Food level before/after
- Comfort level

**Timers set:** `dorm_next_feed` = now + configured interval (4-8 hours)

---

## 14. Dock Census (Data Collection)

**Purpose:** Inventory all ships with their levels, affinities, equipment, and stats.

**Entry state:** `page_dock` (via `page_main`)
**Navigation:** `page_main` → `page_dock` (tap MAIN_GOTO_DOCK_WHITE)

**Substates:**
- `page_dock_grid` — the scrollable ship card grid
- `page_ship_detail` — per-ship detail view (after tapping a ship card)
- `page_ship_gear` — equipment tab within the detail view
- `page_dock_sort` — sort/filter controls overlay

**Sequence (Grid Scan):**
1. Navigate to dock
2. Screenshot the initial grid page
3. Swipe up to scroll (continuous vertical scroll, not paginated)
4. Screenshot after each swipe
5. Detect scroll-end (consecutive identical frames)
6. Repeat until bottom reached

**Sequence (Per-Ship Deep Dive):**
1. Navigate to dock
2. For each ship in the visible grid (row by row, left to right):
   a. Tap ship card → `page_ship_detail`
   b. Screenshot detail page (name, level, affinity, stats, skills, limit break)
   c. Tap gear tab → `page_ship_gear`
   d. Screenshot gear page (all equipment slots in one view)
   e. Tap back → `page_dock_grid`
3. After all visible ships processed, swipe to scroll down
4. Repeat until scroll-end detected or limit reached

**Data read:**
- Ship name, level, rarity, class (from grid cards and detail view)
- Affinity, stats, skills, limit break (from detail view)
- Equipment: name, level, rarity per slot (from gear view)

**Data produced:**
- Timestamped screenshot corpus in `data/census/{timestamp}/`
- Grid page screenshots in `grid/` subdirectory
- Per-ship detail and gear screenshots in `ships/` subdirectory
- SQLite database via offline VLM extraction pipeline

**Decision logic:**
- Scroll calibration: swipe distance tuned to leave 1-2 row overlap
- Scroll-end: raw PNG byte comparison (Vulkan renders identically)
- Ship limit: optional `--limit N` for partial census runs
- Sort/filter: dock sort order affects which ships appear first (configurable pre-step)

**Error patterns:**
- Scroll overshoot: swipe too far, miss ships (mitigated by overlap calibration)
- Tap misalignment: tap wrong grid cell (mitigated by DockLayout calibration)
- Detail view load delay: screenshot captures loading state (mitigated by configurable wait time)

---

## 15. Dorm Rotation (Future Design)

**Purpose:** Rotate ships through dorm slots to farm affinity efficiently.

**Entry state:** `page_dorm`
**Navigation:** `page_main` → `page_dormmenu` → `page_dorm`

**Sequence:**
1. Navigate to dorm
2. Check current dorm occupants (VLM reads ship names/affinity)
3. For each slot: if ship has reached target affinity, swap with next priority ship from the census database
4. Feed ships if food below threshold
5. Return to `page_main`

**Data read:** Current dorm occupants, affinity levels, food bar
**Data produced:** Swap log, affinity progression records
**Decision logic:** Priority queue from census DB (lowest affinity first, or by ship rarity/usefulness)

---

## 16. Secretary Cycling (Future Design)

**Purpose:** Rotate the secretary ship as affinity milestones are reached.

**Entry state:** `page_main` (secretary is visible on main screen)

**Sequence:**
1. Check current secretary's affinity (from census database or live VLM read)
2. If affinity has reached target (e.g., 100 for oath, or a threshold):
   - Navigate to secretary selection
   - Select next priority ship from census DB
   - Confirm selection
3. Return to `page_main`

**Data read:** Current secretary identity, affinity
**Data produced:** Secretary change log, affinity milestone records
**Decision logic:** Rotation order from census DB (prioritize ships needing affinity for oath/pledge)

---

## 17. Commission Tracking (Future Design)

**Purpose:** Accurately track commission dispatches, completions, and resource gains over time.

**Entry state:** `page_commission`
**Navigation:** `page_main` → `page_reward` → `page_commission`

**Sequence:**
1. Navigate to commission page
2. Read all active commissions (VLM extracts name, duration, status, reward icons)
3. Record dispatch times and expected completion times
4. On collection: record actual resource gains (oil, coins, cubes, gems)
5. Track over time in census database (new table: `commissions`)

**Data read:** Commission name, duration, status, reward icons, resource amounts
**Data produced:** Commission log (dispatched, completed, resources gained), efficiency metrics
**Decision logic:** Commission selection from configured priority preset (gem commissions first, shortest duration, etc.)

---

## 18. Equipment Audit (Future Design)

**Purpose:** Track which ships have which equipment, find empty gear slots, identify optimization opportunities.

**Entry state:** derived from dock census deep-dive data

**Sequence:**
1. Run dock census deep-dive (or use existing census data)
2. Extract equipment data via VLM pipeline
3. Query census DB for: empty slots, duplicate equipment, suboptimal gear assignments
4. Generate audit report

**Data read:** Equipment data from census DB
**Data produced:** Audit report (empty slots per ship, gear distribution, optimization suggestions)
**Decision logic:** Gear tier rankings, slot requirements by ship class, BiS (best-in-slot) reference data
