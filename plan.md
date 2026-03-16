# State Cartographer — Master Plan

## What This Is

State Cartographer is a **goal-based automation runtime** for external systems.
It turns "take a screenshot, reason about pixels, click something" into a
deterministic, schedulable, self-recovering automation loop where the tooling
plays the game and the LLM agent supervises.

The runtime stack:

```
Layer 5:   Agent Supervision       (LLM fallback, planning, anomaly handling)
Layer 4.5: Data Collection         (ship census, stat recording, pagination)
Layer 4:   Task Scheduler + Daemon (what runs when, priority queue)
Layer 3:   Task Engine + Resources (task definitions, resource model, executor)
Layer 2:   Navigation Tools        (locate, pathfind, session, observe, calibrate, adb_bridge)
Layer 1:   Schema + Graph          (graph.json, tasks.json, anchors, costs, transitions)
Layer 0:   Libraries               (Pillow, imagehash, ADB, pytransitions)
```

**Reference case:** ALAS (AzurLaneAutoScript) — 43-page state graph, 25+ task
types, priority scheduler, OCR-based resource reading, error recovery via task
injection, 9 years of production use.

## Current Status

**Phase 4 active** — Deterministic navigation piloting against live emulator.

Layers 0-3 are implemented and tested (273 tests passing). Layer 4 scripts
exist but are not yet wired to the live ADB backend. Recording infrastructure
exists (`execution_event_log.py`, `alas_observe_runner.py`,
`alas_event_instrumentation.py`).

---

## Goal-Based Development Phases

Development proceeds through goals, not abstract "layers." Each phase has a
concrete exit criterion that proves the system works at that level.

### Phase 1: Foundation ✅ COMPLETE

**Goal:** Core navigation tools work against test fixtures.

- `locate.py` — passive state classifier
- `pathfind.py` — weighted route planner (Dijkstra)
- `session.py` — state history tracker
- `graph_utils.py` — graph inspection
- `schema_validator.py` — graph.json integrity
- `adb_bridge.py` — ADB screenshot/tap/swipe
- `observe.py` — observation extraction from screenshots
- `calibrate.py` — anchor calibration from real screenshots

**Exit:** 195 tests passing, CI green.

### Phase 2: Schema Validation ✅ COMPLETE

**Goal:** Graph schema represents a real 43-page system without data loss.

- `alas_converter.py` — generates valid graph from ALAS source
- Schema handles multi-locale anchors, bounding boxes, variant states, recovery
- Edge-case fixtures: empty graphs, disconnects, deep chains, self-loops

**Exit:** ALAS graph validates, all Layer 2 tools operate on it correctly.

### Phase 3: Runtime Engine ✅ COMPLETE

**Goal:** Task definitions, scheduling, resource tracking, and execution engine exist.

- `task_model.py` — task manifest load/validate/save
- `resource_model.py` — resource store with threshold gating and timers
- `scheduler.py` — priority-based scheduling with resource constraints
- `executor.py` — task execution with auto session tracking
- `examples/azur-lane/tasks.json` — 11 Azur Lane task definitions
- 78 new tests, all passing

**Exit:** Scheduler picks tasks, executor runs mock sequences, all tests pass.

### Phase 4: Deterministic Navigation Piloting ← ACTIVE

**Goal:** Navigate the live game using the state graph and deterministic tooling.
Retry and loop until we can reliably go from state A to state B using
`pathfind.py` → `adb_bridge.py` taps, confirmed by `locate.py`.

**This is the "write tooling and retry over and over" phase.**

**Workstreams:**

4a. **Live ADB connection**
- Connect executor to real `adb_bridge.py` backend
- Validate screenshot capture works (resolution, format, timing)
- Validate tap/swipe actions reach the emulator

4b. **State classification on live screenshots**
- Run `locate.py` against real screenshots from current emulator
- Identify anchor failures (colors shifted, coordinates wrong)
- Recalibrate anchors using `calibrate.py` with live data
- Record every attempt in NDJSON event log (`execution_event_log.py`)

4c. **Deterministic navigation loops**
- Navigate `page_main` → `page_commission` → `page_main` (known path)
- Navigate `page_main` → `page_research` → `page_main`
- Navigate `page_main` → `page_dorm` → `page_main`
- Navigate `page_main` → `page_guild` → `page_main`
- Navigate `page_main` → `page_meowfficer` → `page_main`
- Navigate `page_main` → `page_private_quarters` → `page_main`
- Navigate `page_main` → `page_exercise` → `page_main`
- Navigate to OpSi map and back
- **Every failure → record screenshot + state + error → fix anchor or path → retry**

4d. **Recording everything**
- `alas_observe_runner.py` captures screenshots + events during piloting
- All navigation attempts logged to NDJSON event stream
- Screenshots saved with metadata to `data/screenshots/`
- Build corpus of labeled state screenshots for future anchor training

**Exit criteria:**
- Can navigate between any two connected states in the graph with >90% success
- All 13+ main pages reachable and classifiable
- Event log captures every action with before/after screenshots
- At least 100 labeled screenshots in corpus

### Phase 5: Vision-Agent Navigation

**Goal:** When deterministic navigation fails (unknown state, misclassified page,
unexpected popup), the vision agent takes over, analyzes the screenshot, and
navigates by reasoning about what it sees.

**This is the fallback layer.** Deterministic first, vision second.

**Workstreams:**

5a. **Unknown state handler**
- When `locate.py` returns `state=unknown` or `confidence < threshold`:
  - Capture high-res screenshot
  - Send to vision agent (Claude with vision) for analysis
  - Agent identifies the current page and suggests recovery action
  - Execute recovery, re-run `locate.py`

5b. **Popup/dialog handler**
- Game has frequent unexpected popups (announcements, updates, maintenance)
- Vision agent identifies popup type and closes it
- Build a popup library over time (template → deterministic dismissal)

5c. **Gesture + swipe navigation**
- Some screens require swipes (dock pagination, OpSi map, dorm floors)
- Record swipe gestures (start_x, start_y, end_x, end_y, duration)
- Library of reusable gesture patterns
- Vision agent verifies scroll position after gesture

5d. **Progressive determinism**
- Every time the vision agent handles a case:
  - Record the screenshot + the action taken
  - If the pattern repeats 3+ times → add it to the graph as a deterministic handler
  - Popups become template matches → taps
  - Unknown states get new anchors added
- Goal: shrink the vision-required set to <5% of transitions

**Exit criteria:**
- Agent can recover from any unknown state within 3 attempts
- Popup dismissal works for all known popup types
- Swipe/gesture library covers dock, OpSi, dorm, formation screens
- <10% of navigations require vision fallback (rest are deterministic)

### Phase 6: Task Execution (Workflow Piloting)

**Goal:** Execute complete Azur Lane workflows end-to-end against the live game.
Not just navigation, but the full task sequence with decision-making.

**Workflows to pilot (in order):**

6a. **Reward collection** — simplest task, pure navigate + tap
6b. **Commission workflow** — navigate → read OCR → select → dispatch → timer
6c. **Research workflow** — navigate → read project info → select → start → timer
6d. **Dorm workflow** — navigate → collect icons → read food → feed → return
6e. **Private Quarters** — navigate → shop → buy gifts → interact → return
6f. **Guild workflow** — navigate → logistics → tech → operations → return
6g. **Daily missions** — navigate → stage select → battle → collect → return
6h. **Meowfficer** — navigate → buy → fort → train → (enhance on Sunday)
6i. **Exercise (PvP)** — navigate → opponent select → battle → return
6j. **Shop workflows** — navigate → read prices → buy priority items → return
6k. **Retire** — navigate → filter → select by rarity → confirm → return
6l. **Operations Siren** — OpsiDaily → OpsiAsh → OpsiObscure → etc.

Each workflow follows the pattern:
```
1. Enable recording (NDJSON event log + screenshots)
2. Navigate to entry state
3. Execute action sequence (taps, OCR reads, decisions)
4. Verify expected outcomes
5. Set timers for next run
6. Navigate back to page_main
7. Review recording, fix any failures, retry
```

**Exit criteria:**
- All 12+ workflows execute successfully at least once on live game
- Each workflow produces correct resource updates
- Timers set correctly for next scheduled run
- Full recording available for review/replay

### Phase 7: Data Collection & Ship Census

**Goal:** Build the "second scheduler" that pages through screens to inventory
all ships, stats, equipment, and skills.

See: `docs/data-collection.md` for full design.

**Workstreams:**

7a. **Pagination engine**
- Generic screenshot → extract → scroll → repeat loop
- End-of-list detection (card count, scroll position, duplicate check)
- Interruptible + resumable (save/restore page index)

7b. **Ship census (dock paging)**
- Dock grid: 7×2 = 14 ships per page
- Per-card: rarity (color), level (OCR), name (OCR), emotion, fleet assignment
- Full dock traversal: 300-500 ships → 25-40 pages
- Output: `data/census/ships.json`

7c. **Ship detail drill-down**
- Tap each ship → stats page → equipment page → skill page
- Per-ship: all 10 stats, 3-5 equipment with enhancement levels, 1-4 skills with levels
- Output: `data/census/ship_details.json`

7d. **Formation audit**
- All fleet compositions (6 fleets × 6 slots each)
- Output: `data/census/formations.json`

7e. **Resource scan**
- Oil, coins, gems from main screen header
- Depot contents from depot screen
- Output: `data/census/resources.json`

7f. **Dorm status audit**
- Comfort level, food level, assigned ships, mood per ship
- Output: `data/census/dorm_status.json`

7g. **OpSi map status**
- Zone exploration status, boss locations, hazard levels
- Output: `data/census/opsi_map.json`

**Exit criteria:**
- Ship census captures >95% of dock accurately
- Ship detail captures stats/equipment/skills for at least 50 ships
- All census data persisted in structured JSON
- Census can be interrupted and resumed

### Phase 8: Scheduling Loop (Full Daemon)

**Goal:** The scheduler runs continuously, picking and executing tasks
automatically, with the data collector running at lower priority between tasks.

**Workstreams:**

8a. **Primary scheduler daemon**
- Infinite loop: `pick_next()` → `execute_task()` → `set_next_run()` → sleep
- Error recovery: failed task → inject restart → retry
- Unknown state → vision agent escalation
- All actions recorded in NDJSON event log

8b. **Data collection interleaving**
- Between primary tasks (when nothing is due for >5 minutes):
  - Run census jobs at low priority
  - Save checkpoint on preemption
  - Resume after primary task completes

8c. **Resource-gated scheduling**
- Don't farm if oil < 200
- Don't retire if dock < 90% full
- Don't buy if gold < threshold

8d. **Timer management**
- Commission timers: collect when complete
- Research timers: collect + start new when complete
- Meowfficer training: check after 2.5-3.5 hours
- Server reset scheduling: daily tasks queue at reset time

**Exit criteria:**
- Scheduler runs for 4+ hours without human intervention
- Completes multiple task cycles (commission → research → dorm → repeat)
- Data collection runs in idle windows
- <5 agent escalations per hour
- All events recorded with before/after screenshots

### Phase 9: Agent Supervision Protocol

**Goal:** Define exactly how the LLM agent supervises the running system.

**Workstreams:**

9a. **Escalation protocol**
- When: unknown state, repeated failure, resource anomaly, new popup type
- How: screenshot + state context + recent event history → agent prompt
- Agent response: recovery action, graph update, task adjustment, or "skip"

9b. **Session review interface**
- `scheduler.format_schedule()` — what's ready/waiting/disabled
- `resource_model` summary — all resource values + timer status
- Event log summary — failures, recoveries, anomalies since last review
- Ship census changes — new ships, level changes, equipment changes

9c. **Between-session handoff**
- What happened since last agent check-in
- What needs manual attention
- Recommended schedule adjustments
- Graph updates from vision agent discoveries

9d. **Planning interface**
- Agent adjusts task priorities
- Agent enables/disables tasks
- Agent configures resource thresholds
- Agent adds new tasks from observed patterns

**Exit criteria:**
- Agent can review a 4-hour session in <5 minutes
- Agent can adjust schedule via structured tools
- Unhandled escalations decrease session-over-session

### Phase 10: Progressive Optimization

**Goal:** The system gets better with use.

1. **Session replay analysis** — which tasks fail most, which transitions are fragile
2. **Anchor recalibration** — automatic when mismatches detected
3. **Task timing optimization** — learn actual durations, adjust intervals
4. **New task discovery** — agent identifies repeatable patterns
5. **Popup library growth** — vision-handled popups → deterministic dismissals
6. **Gesture library growth** — vision-guided swipes → recorded reusable gestures

**Exit criteria:**
- Task success rate improves 10%+ over first 10 sessions
- Vision fallback rate decreases 50%+ over first 10 sessions
- Timer accuracy within 1 minute of actual completion

---

## Complete Workflow Inventory

All Azur Lane workflows the system must handle:

| # | Workflow | Frequency | OCR Required | Gestures | Priority |
|---|---------|-----------|-------------|----------|----------|
| 1 | Restart + Login | On-demand | No | No | CRITICAL |
| 2 | Reward Collection | 15-30 min | Badge detection | No | HIGH |
| 3 | Commission | 60 min | Name, duration, status | No | HIGH |
| 4 | Research | 60-480 min | Name, series, cost | No | HIGH |
| 5 | Dorm | 4-8 hours | Food level, icons | Template match | MEDIUM |
| 6 | Private Quarters | Daily | Inventory, intimacy | No | MEDIUM |
| 7 | Guild | Daily | Contribution, status | No | MEDIUM |
| 8 | Daily Missions | Daily | Stage count, fleet | No | MEDIUM |
| 9 | Exercise (PvP) | 3x daily | Attempts, opponent | No | MEDIUM |
| 10 | Meowfficer | Daily + timers | Count, rarity, timer | No | MEDIUM |
| 11 | Shop (Frequent) | Daily | Prices, gold | No | LOW |
| 12 | Shop (One-time) | Weekly | Prices, gold/gems | No | LOW |
| 13 | Retire | When dock full | Rarity colors | No | LOW |
| 14 | OpSi Daily | Daily | Mission targets | Map scroll | MEDIUM |
| 15 | OpSi Ash | Daily | Beacon status | No | MEDIUM |
| 16 | OpSi Obscure | Weekly | Zone coords | Map scroll | LOW |
| 17 | OpSi Abyssal | Weekly | Boss HP | No | LOW |
| 18 | OpSi Stronghold | Weekly | Boss location | Map scroll | LOW |
| 19 | OpSi Month Boss | Monthly | Adaptability | No | LOW |
| 20 | OpSi Explore | Monthly | Zone status | Map scroll | LOW |
| 21 | Shipyard | Daily | Production slots | No | LOW |
| 22 | Freebies | Event | Various | No | EVENT |
| 23 | Awaken | One-shot | Stage info | No | LOW |
| 24 | Ship Census | Weekly | Level, rarity, name | Dock scroll | DATA |
| 25 | Ship Details | On-demand | All stats, equip, skills | No | DATA |
| 26 | Formation Audit | Daily | Fleet composition | No | DATA |

See: `docs/workflows.md` for detailed per-workflow documentation.

---

## Data Collection Points

Every place in the game where we need to grab data:

### Resource Screens
| Screen | Data | Method |
|--------|------|--------|
| Main screen header | Oil, Coins, Gems | OCR on fixed regions |
| Depot | All items + counts | Pagination + OCR |
| Shop | Prices, inventory | OCR per item |

### Ship Data Screens
| Screen | Data | Method |
|--------|------|--------|
| Dock grid | Rarity, level, name, emotion per card | Color + OCR per card |
| Ship detail: Stats | HP, FP, TRP, AVI, AA, RLD, EVA, SPD, LCK, ACC | OCR all stat fields |
| Ship detail: Equipment | Slot items, enhancement levels, rarity | OCR + color |
| Ship detail: Skills | Skill names, levels (1-10), type | OCR + icon color |
| Ship detail: Affinity | Affinity level + label | OCR |

### Workflow-Specific Data
| Screen | Data | Method |
|--------|------|--------|
| Commission list | Names, durations, rewards, status | OCR + color |
| Research slots | Project names, series, cost, status | OCR + Sobel gradient |
| Dorm | Food level, comfort, ship mood | Custom pixel ratio |
| Private Quarters | Rose/cake count, intimacy | OCR per locale |
| Guild | Contribution, mission status | OCR + color |
| Exercise | Attempt count, opponent power | OCR |
| OpSi map | Zone coords, hazard, exploration status | OCR + color |

### Full Census Pages (require pagination)
| Screen | Items/Page | Scroll Direction | End Detection |
|--------|-----------|-----------------|---------------|
| Dock | 14 (7×2) | Vertical | Card count match header |
| Depot | ~20 items | Vertical | Empty slots |
| Commission list | 4-8 | Tab switch | Tab coverage |
| Research slots | 5 | None | Fixed count |
| Guild members | ~10 | Vertical | Member count |
| OpSi zones | Variable | 2D pan | Zone count |

---

## Recording System

Every action during live piloting is recorded via the existing infrastructure:

- **`execution_event_log.py`** — NDJSON append-only event stream
- **`alas_observe_runner.py`** — passive observation runner (screenshots + events)
- **`alas_event_instrumentation.py`** — monkeypatch recording onto ALAS methods

Event types: `assignment`, `observation`, `execution`, `recovery`

Every event captures: timestamp, run_id, serial, assignment, semantic_action,
primitive_action, state_before, state_after, screen_before, screen_after,
ok, duration_ms, error.

See: `docs/alas-execution-event-schema.md` for full schema.

---

## Architecture

```
Layer 5:   Agent Supervision       (LLM reasoning for planning + anomalies)
Layer 4.5: Data Collection         (ship census, pagination, stat recording)
Layer 4:   Task Scheduler + Daemon (scheduler.py — what runs when)
Layer 3:   Task Engine             (task_model.py, resource_model.py, executor.py)
Layer 2:   Navigation Tools        (locate, pathfind, session, observe, calibrate, adb_bridge)
Layer 1:   Schema + Graph          (graph.json, tasks.json, schema_validator.py)
Layer 0:   Libraries               (Pillow, imagehash, ADB, pytransitions)
```

Each layer depends only on layers below it.

---

## What We're Not Building

- **Agent orchestration framework** — Claude Code etc. manage the agent. We automate the external system.
- **State machine library** — pytransitions handles graph semantics. We extend the data format.
- **Browser/mobile automation** — ADB/Playwright are action backends. We're the layer above.
- **ALAS fork** — ALAS is reference architecture. We generalize the pattern.

---

## Success Metrics

### Phase 4 (Navigation)
- Navigate between any two connected pages with >90% success rate
- 100+ labeled screenshots in corpus
- <2 seconds per deterministic transition

### Phase 6 (Workflow Execution)
- All 12+ primary workflows execute successfully
- Correct resource tracking after each workflow
- Full NDJSON recording of every action

### Phase 7 (Data Collection)
- Ship census captures >95% of dock
- Ship details for 50+ ships
- Census interruptible and resumable

### Phase 8 (Full Daemon)
- 4+ hours autonomous operation
- <5 agent escalations per hour
- Commission + Research + Dorm cycle completes automatically

### Phase 10 (Optimization)
- Vision fallback rate <5%
- Task success rate >95%
- Timer accuracy within 1 minute
