# State Cartographer Redesign — From Navigation Library to Automation Runtime

## The Diagnosis

State Cartographer solves **~10% of the automation problem** and ignores the other 90%.

What it builds: a navigation library. "Where am I?" and "How do I get there?" — locate, pathfind, session tracking. This works. The tests pass. The schema represents ALAS's 43-page graph.

What it ignores: **everything that makes automation actually play the game.**

ALAS — the reference system this project claims to generalize — is not primarily a navigation tool. It is a **task scheduler + game state manager + decision engine**. Navigation is ~10% of its codebase. The other 90%:

| What ALAS Does | State Cartographer Equivalent |
|---|---|
| Task scheduler (NextRun timestamps, priority queue, daemon loop) | **Nothing** |
| Task definitions (commission, research, dorm, daily, hard, exercise...) | **Nothing** |
| Resource tracking (oil, coins, gems, dock capacity via OCR) | **Nothing** |
| Decision engine ("which commission to accept?", "which stage to farm?") | **Nothing** |
| Configuration (per-account, per-server, task enable/disable) | **Nothing** |
| Error recovery as task injection (GameStuckError → inject Restart) | Partial (GOTO_MAIN fallback) |
| Daemon lifecycle (while True: get_next_task → execute → loop) | **Nothing** |

The current MASTER_PLAN.md describes 6 phases. Every phase is about the graph: build it, validate it, optimize it, maintain it. Phase 4 ("Environment Provider Interface") is the closest to runtime, but it's still about plugging in screenshot/tap backends, not about scheduling or game logic.

**The fundamental assumption that's wrong:** "If we build a good enough state graph with deterministic navigation, the agent can do the rest." The agent cannot do the rest. The agent should not have to do the rest. The tooling should execute known task sequences autonomously, and the agent should supervise, plan, and intervene only when something unexpected happens.

---

## What "Playing Azur Lane" Actually Requires

Playing Azur Lane (or any similar game) is a loop:

```
FOREVER:
  1. What tasks are available right now? (scheduler)
  2. Which task should run next? (priority + resource constraints)
  3. Navigate to the task's page (navigation — this is what we have)
  4. Execute the task's action sequence (tap, read, decide, tap, confirm)
  5. Read the result (OCR, pixel check, anchor match)
  6. Update resource state (oil changed, dock changed, timer set)
  7. Set the task's NextRun (now + interval, or server_reset_time)
  8. If error → inject recovery task, retry
  9. Loop
```

Steps 1-2 and 4-8 don't exist in State Cartographer. Step 3 exists. Step 9 (the loop itself) doesn't exist.

### Specific things the user asked about:

- **Where is the scheduler?** → Doesn't exist. No concept of "what runs when."
- **How does it analyze what needs to happen?** → It doesn't. The agent would have to figure this out from scratch every time.
- **How does it track ship girls, money, oil, energy?** → It doesn't. No resource model. No OCR integration. No concept of game state beyond "which screen am I on."
- **When does the next thing turn over?** → No timer awareness. No server-reset knowledge.
- **Does it actually play the game?** → No. It can navigate between screens. That's it.

---

## The Redesign: Three New Layers

The existing work (navigation Layer 1-2) is preserved. Three new layers are added on top:

```
Layer 5: Agent Supervision (LLM fallback + planning + anomaly handling)
Layer 4: Task Scheduler + Daemon Loop (what runs when)
Layer 3: Task Definitions + Resource Model (what each task does + game state)
─────── existing boundary ───────
Layer 2: Runtime Tools (locate, pathfind, session, observe, calibrate, adb_bridge)
Layer 1: Schema + Graph (graph.json, anchors, costs, transitions)
Layer 0: Libraries (Pillow, imagehash, ADB, etc.)
```

### Layer 3: Task Definitions + Resource Model (`scripts/task_engine.py`, `scripts/resource_model.py`)

**Task Definition**: A task is a named, schedulable unit of work with:
- Entry state (which screen to navigate to)
- Action sequence (what to do once there — a list of steps)
- Exit condition (how to know it's done)
- Resource effects (what changes — oil consumed, rewards gained)
- Scheduling rule (when to run next — interval, server reset, one-shot)
- Error strategy (what to do on failure — retry, skip, escalate)

**Resource Model**: A dict of game-state values tracked between tasks:
- Primary: oil, coins, gems, cubes, action points
- Capacity: dock slots, equipment slots
- Timers: commission end times, research end times, dorm morale recovery
- Counts: daily quest progress, weekly boss attempts remaining
- Static: server timezone, reset times

Resources are updated by **observation** (OCR on known screen regions) after each task, not by hardcoded arithmetic. The model is a cache of last-observed values.

### Layer 4: Task Scheduler + Daemon Loop (`scripts/scheduler.py`)

The scheduler is the runtime heart:

```python
def run_loop(graph, tasks, config):
    """Main automation loop. Runs until stopped or all tasks exhausted."""
    while True:
        task = get_next_task(tasks, now(), resources)
        if task is None or task.next_run > now():
            wait_or_idle(task)
            continue
        try:
            navigate_to(graph, task.entry_state)      # Layer 2
            execute_task(task)                          # Layer 3
            update_resources(task)                      # Layer 3
            schedule_next(task)                         # Layer 4
        except RecoverableError:
            inject_recovery_task(tasks)
        except FatalError:
            escalate_to_agent()                        # Layer 5
```

Config: which tasks are enabled, what the priority order is, resource thresholds ("don't farm if oil < 100").

### Layer 5: Agent Supervision

The agent is NOT the loop. The agent is the supervisor:
- **Before the loop**: Agent reviews the task list, adjusts priorities, enables/disables tasks based on goals
- **During the loop**: Agent is called ONLY when the tooling can't handle something (unknown state, new popup, resource decision that needs judgment)
- **Between sessions**: Agent reviews logs, updates the graph, adds new tasks discovered during play
- **Planning**: Agent can look at timers and say "Commission finishes in 42 minutes, Research in 15 — queue Research collection first, then Commission"

The agent does NOT manually call `session.py confirm` after every tap. The tooling does that automatically inside `navigate_to()` and `execute_task()`.

---

## Implementation Plan

### Phase A: Clean Baseline (this session)

1. Merge PR #11 (live state scoring)
2. Get on main, clean working tree
3. Create branch `refactor/automation-runtime`

### Phase B: Core Runtime Scripts (new code)

**B1: `scripts/task_model.py`** — Task data model
- `Task` dataclass: name, entry_state, action_sequence, schedule_rule, error_strategy
- `ScheduleRule`: interval, server_reset, one_shot, cron-like
- `ActionStep`: navigate | tap | wait | read_resource | assert_state | conditional
- Load/save tasks from `tasks.json` alongside `graph.json`

**B2: `scripts/resource_model.py`** — Resource tracking
- `ResourceStore`: dict of name → value with timestamps
- `observe_resources(screenshot, regions)` → updates store from OCR/pixel reading
- `check_threshold(resource, min_value)` → boolean
- Persist to `session.json` alongside state history

**B3: `scripts/scheduler.py`** — The daemon loop
- `get_next_task(tasks, now, resources)` → Task or None
- `run_loop(graph, tasks, config)` → main loop
- Priority ordering, NextRun comparison, resource gating
- Error injection (recovery tasks)
- Hooks for agent escalation

**B4: `scripts/executor.py`** — Task execution engine
- `execute_task(task, graph, adb)` → runs a task's action sequence
- Each ActionStep is dispatched: navigate calls pathfind+adb, tap calls adb_tap, wait is time.sleep, read_resource calls observe
- **Auto session tracking**: every navigation automatically calls session.confirm
- Returns success/failure + resource deltas

**B5: `tasks.json` schema + validator** — Task definitions file
- Companion to graph.json
- Defines all enabled tasks with their action sequences
- `scripts/task_validator.py` + tests

### Phase C: Azur Lane Task Definitions (reference implementation)

**C1: `examples/azur-lane/tasks.json`** — Convert ALAS's key tasks
- Commission (collect + dispatch)
- Research (select + start)  
- Dorm (feed + collect)
- Daily quest (run dailies)
- Reward (collect mail/missions)
- Exercise (PvP battles)

Each task defined with: entry_state, action steps, schedule rule, resource effects.

**C2: Resource regions for Azur Lane** — Where to read oil/coins/etc. from screenshots
- Known screen coordinates for resource displays
- OCR or pixel-bucket reading

### Phase D: Documentation Rewrite

**D1: Rewrite `MASTER_PLAN.md`** — new phases reflect the full automation story
**D2: Rewrite `docs/NORTH_STAR.md`** — vision expands from "navigation" to "automation runtime"
**D3: Rewrite `docs/architecture.md`** — add Layers 3-5
**D4: Rewrite `skills/state-graph-navigation/SKILL.md`** — navigation is now a solved subroutine, not the top-level workflow
**D5: New `skills/task-automation/SKILL.md`** — the real playbook: define tasks, queue them, run the loop, supervise
**D6: Rewrite agent definitions** — explorer discovers tasks AND states, consolidator also builds task definitions, optimizer also tunes schedules
**D7: Rewrite `rules/orientation.md`** — agent doesn't manually track state; tooling does it

### Phase E: Test Suite

- `tests/test_task_model.py` — task loading, validation, serialization
- `tests/test_resource_model.py` — resource observation, thresholds, persistence
- `tests/test_scheduler.py` — priority ordering, NextRun logic, resource gating, error injection
- `tests/test_executor.py` — action sequence execution, auto session tracking
- Integration: scheduler + executor + graph + tasks end-to-end against mock

---

## What Changes vs. What Stays

### STAYS (Layer 1-2 — working, tested, valuable)
- `scripts/locate.py` — still the "where am I?" tool
- `scripts/pathfind.py` — still the route planner
- `scripts/session.py` — still tracks state history (but now called by executor, not by agent)
- `scripts/observe.py` — still extracts observations from screenshots
- `scripts/calibrate.py` — still learns anchor values
- `scripts/adb_bridge.py` — still the ADB wrapper
- `scripts/graph_utils.py` — still the graph inspector
- `scripts/schema_validator.py` — still validates graph.json
- `examples/azur-lane/graph.json` — still the reference state graph
- All existing tests

### CHANGES (new code + doc rewrites)
- New: `scripts/task_model.py`, `scripts/resource_model.py`, `scripts/scheduler.py`, `scripts/executor.py`
- New: `examples/azur-lane/tasks.json`
- New: `skills/task-automation/SKILL.md`
- Rewrite: `MASTER_PLAN.md`, `docs/NORTH_STAR.md`, `docs/architecture.md`
- Rewrite: `rules/orientation.md` (agent no longer manually tracks state)
- Rewrite: agent definitions in `agents/`
- Rewrite: `skills/state-graph-navigation/SKILL.md` (downgrade from "the workflow" to "a subroutine")

### DELETES
- Nothing. All existing code stays. We're adding layers, not replacing them.

---

## Subagent Dispatch Plan

This work requires multiple specialized subagents:

1. **Executor subagent**: Implement `task_model.py`, `resource_model.py`, `scheduler.py`, `executor.py` with tests
2. **Executor subagent**: Create `examples/azur-lane/tasks.json` with commission/research/dorm/daily tasks
3. **Writer subagent**: Rewrite `MASTER_PLAN.md`, `NORTH_STAR.md`, `architecture.md`
4. **Writer subagent**: Create `skills/task-automation/SKILL.md`
5. **Writer subagent**: Rewrite agent definitions + `orientation.md` + navigation SKILL
6. **Verifier subagent**: Run full test suite, verify nothing broke, check coverage

---

## Success Criteria

After this redesign:

1. `python scripts/scheduler.py --graph examples/azur-lane/graph.json --tasks examples/azur-lane/tasks.json --dry-run` shows a scheduled task queue with priorities and NextRun times
2. `python scripts/executor.py --task commission --graph examples/azur-lane/graph.json --mock` executes a mock commission task (navigate to commission screen, simulate collection, update resources)
3. The documentation says "State Cartographer is an automation runtime" not "State Cartographer is a navigation library"
4. An agent reading the new SKILL.md knows: define tasks → configure schedule → run the loop → supervise
5. All existing 186+ tests still pass
6. New tests cover scheduler, executor, task model, resource model
