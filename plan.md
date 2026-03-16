# State Cartographer — Master Plan

## What This Is

State Cartographer is an automation runtime for external systems. It turns "take a screenshot, reason about pixels, click something" into a **scheduled task loop** where the tooling plays the game and the LLM agent supervises.

The runtime has five layers:

```
Layer 5: Agent Supervision (LLM fallback, planning, anomaly handling)
Layer 4: Task Scheduler + Daemon Loop (what runs when)
Layer 3: Task Definitions + Resource Model (what each task does + game state)
Layer 2: Runtime Tools (locate, pathfind, session, observe, calibrate, adb_bridge)
Layer 1: Schema + Graph (graph.json, anchors, costs, transitions)
Layer 0: Libraries (Pillow, imagehash, ADB, pytransitions)
```

## Current Status

**Phase: Runtime Engine Implementation (Active)**

Layers 0-2 are complete and tested (195 tests passing). Layer 3-4 scripts are implemented:
- `scripts/task_model.py` — task data model, load/validate/save
- `scripts/resource_model.py` — resource store with thresholds and timers
- `scripts/scheduler.py` — priority-based scheduling with resource gating
- `scripts/executor.py` — task execution engine with auto session tracking
- `examples/azur-lane/tasks.json` — 11 Azur Lane task definitions

78 new tests cover the runtime engine. All pass.

**Reference case:** ALAS (AzurLaneAutoScript) — 43-page state graph, task scheduler with 15+ task types, priority queue, NextRun timestamps, error recovery via task injection. ALAS proves this pattern works at scale; State Cartographer generalizes it.

---

## Development Phases

### Phase 1: Foundation ✅ COMPLETE

Core navigation tools work correctly against test fixtures.
- `locate.py` classifies states from observation + graph + session data
- `pathfind.py` returns optimal routes via Dijkstra's
- `session.py` tracks state history
- `graph_utils.py` inspects graphs
- `schema_validator.py` catches invalid graph definitions
- `adb_bridge.py` wraps ADB for screenshots and taps
- `observe.py` extracts observations from screenshots
- `calibrate.py` learns anchor values

**Exit:** All tests passing, CI green.

### Phase 2: Schema Validation via ALAS Conversion ✅ COMPLETE

Validated graph.json schema against the real ALAS 43-page state graph.
- `scripts/alas_converter.py` generates valid graph from ALAS source
- Schema handles multi-locale anchors, bounding-box regions, variant states, recovery states
- Edge-case fixtures cover empty graphs, disconnects, deep chains, self-loops

**Exit:** ALAS graph validates, all tools operate on it correctly.

### Phase 3: Runtime Engine ← ACTIVE

Build the task scheduler, executor, resource model, and task definitions.

**3a: Task Model** ✅
- Load/validate tasks.json manifests
- Schedule types: interval, server_reset, one_shot, manual
- Action types: navigate, tap, swipe, wait, wait_until, assert_state, read_resource, conditional, repeat
- Per-task: entry_state, enabled, description, schedule, actions, error_strategy

**3b: Resource Model** ✅
- Resource store with set/get/list
- Threshold checking (min/max gating)
- Timer resources (commission/research completion tracking)
- Persistence (save/load JSON)

**3c: Scheduler** ✅
- `get_ready_tasks()` — enabled + due + resources met
- `pick_next()` — highest priority ready task
- `compute_next_run()` — interval/server_reset/one_shot/manual
- `format_schedule()` — human-readable status
- Default priority: restart > login > reward > commission > research > dorm > ...

**3d: Executor** ✅
- `execute_task()` — entry navigation + action sequence + auto session tracking
- Backend injection for testability (mock_backend vs default_backend)
- Action dispatch for all types (navigate, tap, swipe, wait, wait_until, etc.)
- Entry state navigation is automatic
- session.confirm called automatically after every state change

**3e: Azur Lane Task Definitions** ✅
- 11 tasks: restart, reward, commission, research, dorm, guild, daily, exercise, meowfficer, shop, retire
- Each with schedule, actions, error_strategy, resource requirements

**Remaining in this phase:**
- Documentation rewrite (this file, NORTH_STAR, architecture, skills, agents, rules)
- PR creation and review

### Phase 4: Live Integration

**Goal:** Wire the runtime to a live system and run the full loop.

**Workstreams:**
1. Connect executor to real ADB backend (adb_bridge.py)
2. Add OCR-based resource reading (oil, coins from known screen coordinates)
3. Run scheduler dry-run against live game state
4. Execute single task end-to-end against live system
5. Run multi-task scheduling loop with agent supervision

**Exit:** The tooling autonomously completes at least one full task (e.g., commission collect + dispatch) on a live Azur Lane instance.

### Phase 5: Agent Supervision Protocol

**Goal:** Define how the LLM agent supervises the runtime loop.

**Workstreams:**
1. Define escalation protocol (when does the runtime call the agent?)
2. Build agent planning interface (review schedule, adjust priorities, enable/disable tasks)
3. Implement unknown-state escalation (screenshot + context → agent decides)
4. Session summaries (what happened, what's next, what failed)
5. Between-session handoff (agent reviews logs, updates graph/tasks)

**Exit:** Agent can review and adjust a running automation session via structured tools.

### Phase 6: Progressive Optimization

**Goal:** The system gets better with use.

1. Session replay analysis (which tasks fail most? which transitions are fragile?)
2. Automatic anchor recalibration when mismatches are detected
3. Task timing optimization (learn actual durations, adjust intervals)
4. New task discovery (agent identifies repeatable patterns during supervision)

**Exit:** Measurable improvement in task success rate and cost after 10+ sessions.

---

## Key Workflows

### Workflow: "Set up automation for a new game"

```
1. Build the state graph (explore → consolidate → optimize via authoring skill)
2. Define tasks in tasks.json (entry state, action sequence, schedule)
3. Configure resource regions (where to read oil/coins from screenshots)
4. Run scheduler --dry-run to verify the queue looks right
5. Start the automation loop
6. Agent supervises: handles unknowns, adjusts schedule, adds new tasks
```

### Workflow: "Run the automation loop"

```
1. scheduler.pick_next() → highest priority ready task
2. executor.execute_task() → navigate to entry state, run actions
3. Resource model updated from observations
4. Task's next_run set based on schedule rule
5. If error → error_strategy (retry, skip, restart)
6. If unknown state → escalate to agent
7. Loop
```

### Workflow: "Agent supervision session"

```
1. Review scheduler.format_schedule() — what's ready, what's waiting, what's disabled
2. Check resource_model — oil level, timer expirations
3. Adjust priorities or enable/disable tasks
4. Review error logs from last automated run
5. Update graph if the external system changed
6. Resume the loop
```

---

## Architecture Summary

```
Layer 5: Agent Supervision (LLM reasoning for planning + anomalies)
Layer 4: Scheduler + Daemon (scheduler.py — what runs when)
Layer 3: Task Engine (task_model.py, resource_model.py, executor.py)
Layer 2: Navigation Tools (locate.py, pathfind.py, session.py, observe.py, calibrate.py, adb_bridge.py, graph_utils.py)
Layer 1: Schema (graph.json, tasks.json, schema_validator.py)
Layer 0: Libraries (Pillow, imagehash, ADB, pytransitions)
```

Each layer depends only on layers below it. The scheduler (4) calls the executor (3) which uses navigation tools (2) which operate on the schema (1).

---

## What We're Not Building

- **Agent orchestration framework** — Claude Code, LangGraph, etc. manage the agent. We automate the external system.
- **State machine library** — pytransitions handles graph semantics. We extend the data format.
- **Browser/mobile automation** — Playwright, ADB, Appium are action backends. We're the layer above.
- **ALAS fork** — ALAS is reference architecture. We generalize the pattern.

---

## Success Metrics

- **Autonomous task completion**: tooling completes 80%+ of routine tasks without agent intervention
- **Scheduling accuracy**: tasks run within 1 minute of their scheduled time
- **Navigation cost**: average transition cost <10 (mostly deterministic)
- **Recovery rate**: automatic recovery from known errors in 95%+ of cases
- **Resource tracking**: observed values within 5% of actual for numeric resources
- **Agent involvement**: agent called <5 times per hour of automation
