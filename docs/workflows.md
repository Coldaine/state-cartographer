# Azur Lane Automation Workflows

> This document enumerates every workflow State Cartographer must automate,
> what data each workflow reads, what decisions it makes, and what data it
> produces. This is the ground truth for task definitions and scheduler design.

## Workflow Categories

| Category | Workflows | Frequency |
|----------|-----------|-----------|
| Lifecycle | Restart, Login | On-demand / error recovery |
| Rewards | Reward collect, Mail collect | Every 15-30 min |
| Commissions | Collect + dispatch | Every 60 min |
| Research | Collect + select project | Every 60-480 min |
| Dorm | Feed ships, collect love/coins | Every 4-8 hours |
| Private Quarters | Buy roses/cakes, interact | Daily |
| Guild | Logistics, tech, operations | Daily |
| Daily Missions | Daily Hard/Normal stages | Daily |
| Exercise | PvP battles | 3x daily (reset windows) |
| Meowfficer | Buy, fort chores, train, enhance | Daily + intervals |
| Shops | Frequent shop, one-time shop | Daily / weekly |
| Retire | Dock cleanup by rarity | When dock full |
| Operations Siren | 10+ sub-workflows | Daily / weekly / monthly |
| Data Collection | Ship census, stats, equipment | On-demand |

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

## 6. Private Quarters

**Purpose:** Build intimacy with selected ships via daily interactions.

**Entry state:** `page_private_quarters`
**Navigation:** `page_main` → `page_private_quarters`

**Sequence:**
1. Navigate to private quarters
2. **Shop phase:**
   a. Open PQ shop
   b. Check rose/cake inventory (OCR per-locale)
   c. Buy roses if gold > 24,000 threshold
   d. Buy cakes if gems > 210 threshold
   e. Close shop
3. **Interaction phase:**
   a. Select target ship (configured per slot, 6 slots: Beach + Loft rooms)
   b. Read daily intimacy count (OCR with retry — fast PCs need 3x retries for UI lag)
   c. If interactions remaining:
      - Tap gift button
      - Select rose/cake gift
      - Confirm gift
      - Repeat until daily limit reached
   d. Move to next target ship
4. Return to `page_main`

**Data read:**
- Rose/cake inventory counts (OCR, locale-dependent letter colors)
- Daily interaction counter (OCR with retry)
- Intimacy level per ship
- Shop prices

**Decision logic:**
- Gift priority: roses (cheaper) before cakes (gems)
- Ship priority: highest-intimacy ships first (approaching oath/affinity milestones)
- Server support: TW server unsupported for some PQ features

**Data produced:**
- Intimacy gains per ship per day
- Rose/cake inventory changes
- Gift log

**Timers set:** `private_quarters_next` = next server reset

---

## 7. Guild Workflow

**Purpose:** Collect guild rewards, run logistics, contribute to tech, run guild operations.

**Entry state:** `page_guild`
**Navigation:** `page_main` → `page_guild`

**Sub-pages:** Lobby, Members, Logistics, Tech, Operations (+ Apply if leader)

**Sequence:**
1. Navigate to guild
2. **Logistics:**
   a. Check mission completion status (color inspection on button)
   b. Collect finished missions
   c. Accept new missions
   d. Exchange guild supplies
3. **Tech:**
   a. Donate to guild tech projects
   b. Claim tech rewards
4. **Operations:**
   a. Check guild operation status
   b. Run available operations
   c. Collect operation rewards
5. Determine guild role (leader vs member) via navbar button count
6. If leader: handle apply/member management
7. Return to `page_main`

**Data read:**
- Mission completion buttons (color: green=complete, gray=pending)
- Contribution points (OCR)
- Supply exchange availability
- Navbar button count (determines role)

**Decision logic:**
- Role detection: leader has extra nav buttons
- Logistics: always collect, always accept next
- Tech: donate to cheapest incomplete project
- Operations: run if available, skip if already running

**Data produced:**
- Guild contribution totals
- Mission rewards collected
- Supply exchange log

---

## 8. Daily Missions

**Purpose:** Complete daily combat missions for rewards.

**Entry state:** `page_daily`
**Navigation:** `page_main` → `page_campaign` → `page_daily`

**Sequence:**
1. Navigate to daily mission screen
2. Read available daily stages (3-7 depending on day + events)
3. For each configured stage:
   a. Check if stage is active (`is_active()` — brightness > 30)
   b. Read remaining attempts (OCR)
   c. If attempts > 0:
      - Select stage
      - Choose fleet (configurable fleet index)
      - Start battle
      - Wait for battle completion
      - Collect rewards
4. Return to `page_main`

**Data read:**
- Stage active status (average brightness of DAILY_ACTIVE area)
- Remaining attempt count (OCR)
- Fleet index for each stage (OCR)
- Battle result (victory/defeat)

**Decision logic:**
- Stage selection: configured per day-of-week
- Fleet assignment: mapped per stage type
- Skip conditions: no remaining attempts, stage not active

---

## 9. Exercise (PvP)

**Purpose:** Complete PvP exercise battles.

**Entry state:** `page_exercise`
**Navigation:** `page_main` → `page_exercise`

**Sequence:**
1. Navigate to exercise page
2. Read exercise attempt count (resets 3x daily)
3. For each available attempt:
   a. Select opponent (usually weakest available)
   b. Choose fleet
   c. Start battle
   d. Handle battle (auto or manual fleet selection)
   e. Record win/loss
4. Return to `page_main`

**Data read:**
- Exercise attempt count
- Opponent fleet power
- Win/loss result

---

## 10. Meowfficer Workflow

**Purpose:** Manage Meowfficer training, purchases, and fort chores.

**Entry state:** `page_meowfficer`
**Navigation:** `page_main` → `page_meowfficer`

**Sequence (ordered):**
1. **Buy phase:**
   a. Open Meowfficer shop
   b. Purchase available Meowfficer boxes (configured count)
   c. Close shop
2. **Fort chores:**
   a. Navigate to fort
   b. Collect completed chore rewards
   c. Assign new chores
3. **Training:**
   a. Check training status
   b. If complete: collect trained Meowfficer
   c. Start new training if slots available
   d. Record training completion timer
4. **Enhance (Sunday only):**
   a. Merge surplus Meowfficers into priority ones
   b. Select enhance targets based on rarity + skills

**Data read:**
- Meowfficer count
- Training completion timer
- Rarity distribution (color-based)
- Fort chore status

**Decision logic:**
- Buy count: configurable (0-3 per day)
- Training priority: highest rarity first
- Enhance: only on Sundays (game restriction)
- Wait for training: scheduler delays 2.5-3.5 hours

**Timers set:** `meowfficer_training_complete`

---

## 11. Shop Workflows

**Purpose:** Purchase daily/weekly items from shops.

### Frequent Shop (daily)
- Buy food, plates, and T3 skill books
- Read prices (OCR), check gold budget
- Buy in priority order

### One-Time Shop (weekly reset)
- Buy cubes, gold boxes, T4 books
- More expensive items, tighter budget logic

**Data read:** Item prices, inventory counts, gold/gem balance
**Timers set:** `shop_frequent_next` = daily reset, `shop_once_next` = weekly reset

---

## 12. Retire / Dock Cleanup

**Purpose:** Retire low-rarity ships to free dock space.

**Entry state:** `page_retire`
**Navigation:** `page_main` → `page_dock` → `page_retire`

**Sequence:**
1. Open dock in retire mode
2. Apply rarity filter (select N/R based on config)
3. Grid layout: 7×2 = 14 ships per page
4. Scan each ship card:
   a. Read rarity via color sampling (gray=N, blue=R, purple=SR, gold=SSR)
   b. Match against configured retirement rarity
5. Select ships for retirement (up to batch limit)
6. Confirm retirement (multi-step confirmation screen)
7. Record resource gains (coins, oil, retrofit items)
8. Repeat if more ships remain
9. Return to `page_main`

**Data read:**
- Ship rarity colors (RGB threshold ±15)
- Ship count in dock
- Resource gains from retirement

**Decision logic:**
- Rarity filter: N always, R optional, SR/SSR never (configurable)
- GemsFarming protection: don't retire CVs if GemsFarming enabled
- Batch size: game limits per retirement batch

---

## 13. Operations Siren (Full Scope)

OpSi is the most complex workflow family. It operates on a separate world map
with zones, ports, bosses, and monthly resets.

### 13a. OpsiDaily
- Complete 8 daily missions from OpSi mission board
- Read mission targets (zone coordinates, mission type)
- Navigate to zones, complete objectives, return to port

### 13b. OpsiAshBeacon + OpsiAshAssist
- Collect Ash beacons from a storage system
- Assist other players' Ash fights
- Coordinate collection timing

### 13c. OpsiObscure
- Find and clear obscure/secret zones
- Zone coordinates stored between sessions
- Combat with boss encounters

### 13d. OpsiAbyssal
- Engage abyssal boss encounters
- Multi-fleet retry logic (switch fleets on failure)
- Track defeat patterns

### 13e. OpsiArchive
- Purchase weekly logger archive entries
- Resets on Wednesdays
- Resource cost evaluation

### 13f. OpsiStronghold
- Locate and attack Siren stronghold bosses
- Multi-fleet combat with adaptability scoring
- Zone searching + navigation

### 13g. OpsiMonthBoss
- Monthly endgame boss with Normal and Hard modes
- Requires adaptability threshold checks
- Fleets must meet minimum power requirements

### 13h. OpsiMeowfficerFarming
- Grind Hazard 1-5 zones for Meowfficer drops
- Smart zone selection (prefer cheapest oil cost)
- Long-running farming loop

### 13i. OpsiExplore
- Month-start exploration of all dangerous zones
- Resumable (tracks explored zones across sessions)
- Systematic coverage of world map

### 13j. OpsiCrossMonth
- Handle monthly reset synchronization
- Waits for server reset with 60s polling within 10-minute window
- Ensures clean monthly transition

**Data read (OpSi common):**
- Zone coordinates, mission markers on globe
- Fleet power + adaptability scores
- Resource costs (oil, action points)
- Boss HP bars and completion status
- Port daily mission list

---

## Missing Workflows (Not Yet in tasks.json)

These workflows exist in ALAS but are not yet represented in our task definitions:

| Workflow | ALAS Module | Priority |
|----------|-------------|----------|
| Private Quarters | `module/private_quarters/` | HIGH |
| OpsiDaily | `module/os/` | HIGH |
| OpsiAshBeacon | `module/os/` | MEDIUM |
| OpsiExplore | `module/os/` | MEDIUM |
| OpsiMeowfficerFarming | `module/os/` | LOW |
| ShopFrequent | `module/shop/` | MEDIUM |
| ShopOnce | `module/shop/` | LOW |
| Shipyard | `module/` | LOW |
| Freebies | `module/` | MEDIUM |
| Awaken | `module/` | LOW |
| Campaign stages | `module/campaign/` | LOW |
| Event stages | `module/campaign/event_*/` | EVENT |

---

## Data Flow Summary

Every workflow follows the same fundamental pattern:

```
Screenshot → Crop Region → OCR/Color/Template → Parse → Filter/Decision → Tap → Next
```

The runtime must support:
1. **Screenshot capture** — via ADB (`adb_bridge.py`)
2. **Region extraction** — crop to known coordinates
3. **Recognition** — OCR (text), color sampling (status), template matching (icons)
4. **Decision** — config-driven rules applied to extracted data
5. **Action** — tap, swipe, long-press at computed coordinates
6. **State verify** — screenshot again, confirm expected state reached
7. **Record** — log the event, update resources, set timers
