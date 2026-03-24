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
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)

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
