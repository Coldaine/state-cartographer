# Architecture: Capability-to-Layer Mapping

State Cartographer is an automation runtime with seven layers. Layers 0-2 handle navigation (the original scope). Layers 3-5 handle task automation (the runtime engine). Layer 4.5 handles data collection (ship census, stat recording).

```
Layer 5:   Agent Supervision       (LLM reasoning for planning + anomaly handling)
Layer 4.5: Data Collection         (ship census, pagination, stat recording)
Layer 4:   Task Scheduler + Daemon (what runs when, priority queue)
Layer 3:   Task Engine + Resources (task definitions, resource model, executor)
───────── automation boundary ─────────
Layer 2:   Runtime Navigation Tools (locate, pathfind, session, observe, calibrate, adb_bridge)
Layer 1:   Schema + Graph          (graph.json, tasks.json, anchors, costs, transitions)
Layer 0:   Libraries               (pytransitions, Pillow, imagehash, ADB)
```

## Layer 0: Don't Build (Use Existing)

These are solved problems. Pick an implementation, don't reinvent.

- **State graph definition**: states, transitions, guards, hierarchical/parallel states, history → SCXML spec, implemented by XState (TS) or pytransitions/python-statemachine (Python)
- **Introspection**: "what transitions are valid from state X?", "is this state a substate of Y?" → built into XState (`state.matches()`, `state.can()`) and pytransitions (`get_triggers()`, `may_trigger()`)
- **Serialization**: save/load the graph definition → XState JSON format, pytransitions dict-based config
- **Visualization**: render the graph for human review → XState's Stately Studio, pytransitions' Mermaid/graphviz export
- **Action execution**: actually clicking buttons, navigating URLs, tapping ADB coordinates → Playwright (web), Appium (mobile), ADB (Android), accessibility APIs (desktop), subprocess (CLI)

**Decision needed**: Python or TypeScript as primary runtime? Python has the richer ML/automation ecosystem. TypeScript has XState which is the most complete statechart implementation. The skill itself is language-agnostic (it's methodology + scripts), but the runtime tools need a language.

Recommendation: **Python with pytransitions as the graph engine.** Rationale: most AI agent tooling is Python; pytransitions has the richest introspection API in Python; the action execution layer (ADB, Playwright Python bindings, subprocess) is overwhelmingly Python. XState's JSON format can still be used as the canonical definition format and loaded into pytransitions.

---

## Layer 1: Schema Extensions (data format, lives in references/)

Extends the state machine definition with fields no existing library supports. This is a **data format spec** that wraps around the base state machine definition.

### 1a. Observation Anchors

Per-state annotations for confirming "you are in this state."

```yaml
states:
  main_menu:
    anchors:
      - type: dom_element
        selector: "#main-menu-container"
        cost: 1  # cheapest
      - type: text_match
        pattern: "Welcome, Commander"
        cost: 2
      - type: screenshot_region
        bbox: [0, 0, 100, 50]
        expected_hash: "a3f2..."  # perceptual hash
        cost: 5  # more expensive
    negative_anchors:
      - type: dom_element
        selector: ".loading-spinner"
        # if this is present, definitely NOT main_menu
```

**Novel capability #2 from our enumeration.**

### 1b. Transition Cost Annotations

Per-transition cost profile.

```yaml
transitions:
  main_menu_to_dock:
    method: deterministic
    action: { type: adb_tap, x: 450, y: 800 }
    cost: 1
    latency_ms: 200
  dock_to_ship_detail:
    method: vision_required
    action: { type: screenshot_then_click, description: "find and tap target ship" }
    cost: 50
    latency_ms: 3000
    fragile: true
    fallback: vision_full
```

**Novel capability #5.**

### 1c. Wait State Annotations

```yaml
states:
  auto_battle:
    wait_state: true
    expected_duration_range: [30000, 120000]  # ms
    poll_interval: 5000
    exit_signals:
      - type: dom_element
        selector: ".battle-result-screen"
      - type: text_match
        pattern: "Victory|Defeat"
    timeout_behavior: escalate_to_vision
```

**Novel capability #8.**

### 1d. Confidence Thresholds

```yaml
states:
  purchase_confirm:
    confidence_threshold: 0.99
    on_low_confidence: vision_review
    irreversible: true
  main_menu:
    confidence_threshold: 0.7
    on_low_confidence: proceed_with_warning
```

**Novel capability #11.**

### Schema spec document location: `skills/state-graph-authoring/references/schema.md`
Comprehensive spec for all extension fields. Loaded on demand when the agent is building or editing a state graph definition.

---

## Layer 2: Runtime Tools (Python scripts in scripts/)

Deterministic tooling the agent calls. These are the hard tools that do real work.

### 2a. `locate.py` — Passive State Classifier

The core tool. Called by the agent as `python scripts/locate.py --graph graph.json --session session.json --observations obs.json`.

Input:
- The state graph definition (with anchors)
- Current session history (sequence of confirmed states + transitions so far)
- Current observations (whatever signals are available right now)

Output (JSON):
- `{ "state": "main_menu", "confidence": 0.95 }` if definitive
- `{ "candidates": [{"state": "dock", "confidence": 0.6}, {"state": "formation", "confidence": 0.3}], "disambiguation": [{"action": "check_dom_element", "selector": "#dock-header", "resolves": "dock"}, {"action": "press_back", "observe": "response"}] }` if ambiguous

Logic:
1. If session history constrains to one possible state → return it (cheapest path)
2. Otherwise, evaluate anchors in cost order for all candidate states
3. Prune candidates via negative anchors
4. If one candidate has confidence above threshold → return it
5. If ambiguous → return candidate set with ranked disambiguation probes

**Novel capabilities #3 and #4.**

### 2b. `pathfind.py` — Weighted Route Planner

`python scripts/pathfind.py --graph graph.json --from current_state --to target_state`

Output: ordered sequence of transitions with total cost, using Dijkstra or A* over transition cost annotations.

Also supports: `--avoid state_name` (route around known-broken states), `--prefer deterministic` (bias toward cheap transitions even if more hops).

**Novel capability #6.**

### 2c. `session.py` — Session Manager

Maintains the running record of confirmed states and transitions for the current automation session. Used by `locate.py` to constrain candidates.

- `python scripts/session.py init --graph graph.json` → creates session.json
- `python scripts/session.py confirm --state main_menu` → records confirmed state
- `python scripts/session.py transition --event tap_dock` → records transition taken
- `python scripts/session.py query` → returns current session state and history

**Part of novel capability #3 (session awareness for locate).**

### 2d. `screenshot_mock.py` — Screenshot Mock Manager

Manages the offline development dataset.

- `python scripts/screenshot_mock.py capture --state main_menu --file screenshot.png` → associates screenshot with state
- `python scripts/screenshot_mock.py validate --graph graph.json` → runs all anchors against all captured screenshots, reports which states have good coverage and which anchors fail
- `python scripts/screenshot_mock.py test-locate --graph graph.json --screenshot screenshot.png` → tests the locate classifier against a known-state screenshot

**Novel capability #10.**

### 2e. `graph_utils.py` — Graph Inspection Utilities

Wraps pytransitions for common queries the agent needs:
- List all states
- List valid transitions from a state
- List all states reachable from a state within N hops
- Identify orphan states (no inbound transitions)
- Identify states missing anchors
- Identify transitions missing cost annotations
- Export to Mermaid for visualization

Thin wrapper, but saves the agent from having to write pytransitions boilerplate every time.

---

## Layer 3: The SKILL.md Itself (the playbook)

This is the methodology layer. ~500 lines. Always loaded when the skill triggers. Tells the agent **how** to do the work, not what the tools are (that's in references/).

### Structure:

```
SKILL.md
├── Frontmatter (name, description, triggers)
├── Overview: what this skill does and when to use it
├── Quick orientation: "where are you in the process?"
│   Decision tree for whether to explore, consolidate, optimize, or maintain
├── Phase 1: Exploration
│   - How to navigate systematically
│   - What to record at each state (screenshot, DOM dump, observation notes)
│   - How to detect "new state" vs "same state, different content"
│   - When to use the mock capture tool
│   - How to build the initial graph definition
├── Phase 2: Consolidation
│   - How to identify stable anchors vs transient content
│   - How to merge states that are "the same"
│   - How to split states that look the same but aren't
│   - When to ask the human for input
│   - How to validate anchors using screenshot_mock.py
├── Phase 3: Transition Replacement
│   - How to identify candidates for deterministic replacement
│   - Common patterns (back button, menu button, confirm dialog)
│   - How to test a replaced transition
│   - How to annotate costs
├── Phase 4: Wait State Identification
│   - Signals that a state is a wait state
│   - How to determine polling interval and exit signals
│   - How to set timeout behavior
├── Phase 5: Orientation Layer
│   - How to design anchor hierarchies (cheap first)
│   - How to use locate.py
│   - How to use session.py
│   - How to handle disambiguation results
├── Phase 6: Maintenance
│   - How to detect graph drift
│   - How to update anchors when the external system changes
│   - How to add new states discovered during operation
├── Tool reference (brief, pointers to scripts/)
└── Pointers to references/ for deeper docs
```

**Novel capability #12 (the playbook).**

---

## Layer 4: Agent Role Definitions (references/)

Progressive disclosure: only loaded when the agent is doing that specific role's work.

### `references/schema.md`
Full specification of all schema extensions (anchors, costs, wait states, confidence thresholds). The canonical reference for the data format.

### `references/explorer.md`
Instructions for the exploration phase. How to systematically navigate an unknown system, what to capture at each state, how to handle errors during exploration, how to structure exploration for maximum coverage with minimum redundancy.

### `references/consolidator.md`
Instructions for the consolidation phase. Decision criteria for merging/splitting states. How to identify stable anchors. How to use screenshot_mock.py validate. Specific patterns to watch for (rotating content, context-dependent dialogs, loading states that masquerade as real states).

### `references/optimizer.md`
Instructions for the transition replacement pass. How to analyze each transition for replacement candidates. How to write and test deterministic action implementations. How to annotate costs. How to verify that the replaced transition reliably reaches the expected target state.

### `references/troubleshooting.md`
Common problems: locate() always returns ambiguous, graph drift after app update, transition that worked yesterday fails today, session desync. Diagnostic steps and fixes.

**Novel capability #13 (multi-agent decomposition).**

---

## What This Looks Like on Disk

```
state-cartographer/
├── SKILL.md                    (~500 lines, the playbook)
├── scripts/
│   ├── locate.py               (passive state classifier)
│   ├── pathfind.py             (weighted route planner)
│   ├── session.py              (session manager)
│   ├── screenshot_mock.py      (screenshot mock manager)
│   ├── graph_utils.py          (pytransitions wrapper)
│   ├── adb_bridge.py           (ADB provider and screenshot bridge)
│   ├── observe.py              (observation extraction)
│   └── calibrate.py            (anchor calibration)
├── references/
│   ├── schema.md               (full schema extension spec)
│   ├── explorer.md             (exploration phase instructions)
│   ├── consolidator.md         (consolidation phase instructions)
│   ├── optimizer.md            (transition replacement instructions)
│   └── troubleshooting.md      (common problems and fixes)
└── assets/
    └── templates/
        └── graph-template.json (starter graph definition)
```

---

## Layer 3: Task Definitions + Resource Model (`scripts/task_model.py`, `scripts/resource_model.py`, `scripts/executor.py`)

The task layer turns navigation into automation. Instead of "navigate to commission screen," the question becomes "run the commission task: navigate there, collect rewards, dispatch new commissions, update resource state, schedule the next run."

### 3a. Task Model (`scripts/task_model.py`)

A task is a named, schedulable unit of work:

```json
{
  "commission": {
    "entry_state": "page_commission",
    "enabled": true,
    "schedule": { "type": "interval", "minutes": 60 },
    "actions": [
      { "action": "tap", "x": 600, "y": 400, "description": "Collect all" },
      { "action": "wait", "seconds": 2 },
      { "action": "tap", "x": 600, "y": 500, "description": "Dispatch" }
    ],
    "error_strategy": "restart"
  }
}
```

Functions:
- `load_tasks(path)` — load and validate tasks.json
- `validate_task_manifest(manifest)` — check required keys, schedule types, action types
- `get_task()`, `is_task_enabled()`, `get_next_run()`, `set_next_run()`

Schedule types: `interval` (every N minutes), `server_reset` (daily at server reset time), `one_shot` (run once then disable), `manual` (agent-triggered only).

Action types: `navigate`, `tap`, `swipe`, `wait`, `wait_until`, `assert_state`, `read_resource`, `conditional`, `repeat`.

### 3b. Resource Model (`scripts/resource_model.py`)

A resource store tracks game state values between tasks:

```python
store = create_store()
set_resource(store, "oil", 8500, source="ocr")
set_resource(store, "coins", 42000, source="ocr")
set_timer(store, "commission_1", expires_at)

check_threshold(store, "oil", min_value=200)  # → True
is_timer_expired(store, "commission_1")        # → False
```

Resources are updated by observation (OCR, pixel check) after each task, not by arithmetic. The model is a cache of last-observed values.

Functions:
- `create_store()`, `set_resource()`, `get_resource()`, `get_value()`
- `check_threshold(store, name, min_value, max_value)` — for scheduler gating
- `set_timer()`, `is_timer_expired()` — for commission/research completion tracking
- `save_store()`, `load_store()` — JSON persistence

### 3c. Task Executor (`scripts/executor.py`)

Runs a task's action sequence with automatic state tracking:

```python
result = execute_task(task_def, graph, session, backend)
# → navigates to entry_state (calls pathfind + adb_bridge)
# → executes each action in sequence
# → calls session.confirm automatically after state changes
# → returns {"success": True, "actions_completed": 5}
```

Backend injection pattern for testability:
- `mock_backend()` — logs all actions, returns success (for tests)
- `default_backend()` — wires to real pathfind.py, adb_bridge.py, locate.py

---

## Layer 4: Task Scheduler (`scripts/scheduler.py`)

The scheduler is the runtime heart. It decides what runs when.

```python
ready = get_ready_tasks(manifest, now, resources)    # enabled + due + resources met
task = pick_next(manifest, now, resources)            # highest priority ready task
next_run = compute_next_run(task_def, now)            # when to run again
wakeup = next_wakeup(manifest, now)                   # when to check again
```

**Priority order** (configurable, default):
restart > login > reward > commission > research > dorm > meowfficer > guild > daily > hard > exercise > event > campaign > retire > shop

**Resource gating**: A task can declare resource requirements (`"requires": {"oil": {"min": 200}}`). The scheduler checks these before marking the task as ready.

**Schedule computation**:
- `interval` → now + N minutes
- `server_reset` → next server reset time (configurable timezone + hour)
- `one_shot` → datetime.max (run once, never again)
- `manual` → None (only runs when agent explicitly triggers)

CLI: `python scripts/scheduler.py --tasks tasks.json --resources store.json --dry-run`

---

## Layer 4.5: Data Collection Scheduler

A second scheduling loop dedicated to **read-heavy, pagination-driven** data
gathering. Sits between the task scheduler and agent supervision because it
uses navigation tools (Layer 2) but produces data for agent decisions (Layer 5).

**Why separate from Layer 4?**
- Pagination workflows (dock census, depot scan) are fundamentally different from
  fire-and-forget tasks (collect commissions, feed dorm)
- Data collection is interruptible and resumable (save page index, restart later)
- Must yield to the primary scheduler when urgent tasks become ready

**Jobs:**
- `ship_census` — page through dock, read rarity/level/name per card (7×2 grid, 25-40 pages)
- `ship_detail` — tap each ship, read stats/equipment/skills from detail pages
- `formation_audit` — record all fleet compositions
- `resource_scan` — read oil/coins/gems from main screen + depot
- `dorm_status` — comfort, food level, assigned ships, mood
- `guild_roster` — page through guild member list
- `opsi_map` — record zone exploration/completion status

**Pagination engine:** Generic `screenshot → extract → scroll → repeat` loop with
end-of-list detection (card count vs header, scroll position, duplicate frame).

**Preemption:** When primary scheduler has a task ready, data collection pauses
(saves checkpoint), defers to primary task, then resumes from checkpoint.

See: `docs/data-collection.md` for full design.

---

## Layer 5: Agent Supervision

The agent is NOT the loop. The agent is the supervisor.

- **Before the loop**: Review task list, adjust priorities, enable/disable tasks
- **During the loop**: Called ONLY when tooling can't handle something (unknown state, new popup, resource decision needing judgment)
- **Vision fallback**: When deterministic navigation fails, the vision agent analyzes the screenshot and suggests recovery. Patterns that repeat 3+ times get promoted to deterministic graph entries.
- **Between sessions**: Review logs, update graph, add new tasks discovered during play
- **Planning**: "Commission finishes in 42 minutes, Research in 15 — queue Research collection first"
- **Census review**: Analyze ship stats to recommend fleet compositions, equipment swaps, skill training priorities

The agent does NOT manually call `session.py confirm` after every tap. The executor does that automatically.

---

## Layer Dependency Chain

```
Layer 0 (existing libs)
  └── pytransitions, Playwright/ADB/etc., Pillow, imagehash
       │
Layer 1 (schema + data)
  └── graph.json (states, transitions, anchors, costs)
  └── tasks.json (task definitions, schedules, actions)
       │
Layer 2 (navigation tools)
  └── locate.py, pathfind.py, session.py, observe.py, calibrate.py, adb_bridge.py, graph_utils.py
       │
Layer 3 (task engine)
  └── task_model.py, resource_model.py, executor.py
  └── Uses Layer 2 for navigation, adds scheduling + execution
       │
Layer 4 (scheduler)
  └── scheduler.py — picks tasks, checks resources, computes next runs
  └── Calls Layer 3 executor to run tasks
       │
Layer 4.5 (data collection)
  └── data_collector.py — pagination jobs, census, stat recording
  └── Uses Layer 2 for navigation, produces data for Layer 5
  └── Yields to Layer 4 when primary tasks are due
       │
Layer 5 (agent supervision)
  └── LLM agent reviews schedule, handles unknowns, adjusts priorities
  └── Called by Layer 4 on escalation
  └── Analyzes Layer 4.5 census data for planning
```
