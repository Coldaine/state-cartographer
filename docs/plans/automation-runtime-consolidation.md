# Automation Runtime Consolidation Plan

> Written 2026-03-19, updated 2026-03-19. Branch: `refactor/automation-runtime`

## Design North Star

The updated documentation (`NORTH_STAR.md`, `architecture.md`, `plan.md`,
`CLAUDE.md`) defines a clear **agent control surface** with three tiers:

1. **High-level runtime calls**: `execute_task("commission")`,
   `navigate_to("page_dorm")`, `ensure_game_ready()`
2. **Supervisory queries**: `where_am_i()`,
   `why_did_last_transition_fail()`, `show_recent_failures()`
3. **Escalation payloads** pushed up by the runtime: screenshot + candidates +
   recent actions + proposed recovery paths

**Ownership boundary**: The runtime/backend owns screenshot capture, low-level
emulator I/O, state verification, and event logging. The agent does not manually
request screenshots or stitch raw taps into workflows during normal operation.
Direct CLI use of `locate.py`, `observe.py`, etc. remains valid for debugging,
calibration, and the current exploration phase — but is not the steady-state
operating model.

**ALAS is reference architecture and optional observation source**, not the
live control plane. The live control path is State Cartographer's own
executor/backend stack.

## Status Assessment

The redesign from navigation library to automation runtime (proposed in
`docs/redesign-plan.md`) has been **largely executed**. The four core runtime
scripts exist with tests, the Azur Lane task definitions exist, and all docs
have been rewritten. But the pieces are **fragmented** — they work in isolation
but aren't wired into a runnable system. And the agent control surface described
above does not exist as callable code.

### What's Done (Phases B-E of redesign)

| Deliverable | Status | Location |
|-------------|--------|----------|
| Task model + validation | Done, 12 tests | `scripts/task_model.py` |
| Resource model + timers | Done, 16 tests | `scripts/resource_model.py` |
| Scheduler (pick_next, priority, resource gating) | Done, 13 tests | `scripts/scheduler.py` |
| Executor (action dispatch, mock backend, auto session) | Done, 11 tests | `scripts/executor.py` |
| Azur Lane task definitions (11 tasks) | Done | `examples/azur-lane/tasks.json` |
| Task automation skill | Done | `skills/task-automation/SKILL.md` |
| Navigation skill (downgraded to subroutine) | Done | `skills/state-graph-navigation/SKILL.md` |
| Architecture docs (Layers 0-5 + 4.5) | Done | `docs/architecture.md` |
| North Star (automation runtime vision) | Done | `docs/NORTH_STAR.md` |
| Orientation rule (executor handles automatically) | Done | `rules/orientation.md` |
| Agent definitions (task discovery, schedule tuning) | Done | `agents/*.md` |
| Master plan (10 goal-based phases) | Done | `plan.md` |
| Workflow inventory (26 workflows documented) | Done | `docs/workflows.md` |

### What's Fragmented

The pieces exist but don't connect into a runnable whole. These are the real
gaps blocking Phase 4 (live deterministic piloting):

---

## Gap 1: No Daemon Loop (BLOCKING)

**Problem:** `scheduler.py` has `pick_next()` and `executor.py` has
`execute_task()`, but nothing wires them into a `while True` loop. The
`skills/task-automation/SKILL.md` shows a loop in pseudocode but it doesn't
exist as runnable code.

**What's needed:** A `scripts/daemon.py` (or `run_loop()` in scheduler.py) that:
1. Calls `pick_next()` to get the next task
2. Calls `execute_task()` to run it
3. Calls `compute_next_run()` to schedule the next execution
4. Saves the updated manifest
5. Sleeps until the next wakeup
6. Handles errors via task error_strategy
7. Logs everything to the NDJSON event log

**Estimated scope:** ~150 lines. Glue code, not new logic.

---

## Gap 2: Error Strategy Not Enforced (BLOCKING)

**Problem:** Tasks define `error_strategy` (retry, restart, skip, escalate) but
nothing reads it. When `execute_task()` returns `{"success": false}`, the caller
gets the error but there's no automatic handling.

**What's needed:** The daemon loop (Gap 1) must implement:
- `"retry"` → re-run the task (max 3 attempts)
- `"restart"` → inject a restart task at head of queue, then retry
- `"skip"` → log and move on, schedule next run normally
- `"escalate"` → call agent escalation hook (Gap 3)

**Estimated scope:** ~50 lines inside the daemon loop.

---

## Gap 3: No Agent Escalation Mechanism (IMPORTANT)

**Problem:** When the executor hits an unknown state or repeated failures, plan.md
says "escalate to agent." But there's no escalation hook — no callback, no
event, no way to pause the loop and ask for help.

**What's needed:** An escalation protocol:
- Executor/daemon emits an escalation event to the NDJSON log
- Daemon pauses (doesn't crash, just waits)
- Agent reads the escalation, investigates, takes action
- Agent signals "resume" (or manually triggers next task)

For now, simplest implementation: daemon prints escalation to stdout and pauses
with a configurable timeout. The agent (Claude Code) can read the output and
intervene.

**Estimated scope:** ~30 lines. Can be a simple callback pattern.

---

## Gap 4: Event Recording Not Wired to Executor (IMPORTANT)

**Problem:** Three recording scripts exist (`execution_event_log.py`,
`alas_observe_runner.py`, `alas_event_instrumentation.py`) but they're not
called by the executor or scheduler. The executor runs tasks silently — no
before/after screenshots, no event log entries.

**What's needed:** The executor's backend functions should emit events:
- Before each action: capture screenshot, log intent
- After each action: capture screenshot, log result
- On state change: log transition
- On error: log failure with screenshot

This can be done by wrapping the backend functions or adding event hooks to
`execute_task()`.

**Estimated scope:** ~80 lines. Backend wrapper pattern.

---

## Gap 5: `read_resource` Action Is a Placeholder (IMPORTANT)

**Problem:** The executor's `read_resource` action type returns
`{"success": True}` and does nothing. No OCR, no pixel reading, no resource
observation.

**What's needed:** Wire `read_resource` to `observe.py` or a new OCR module.
For Phase 4, even a stub that reads from known screen regions via pixel
color checking would be sufficient. Full OCR can come in Phase 6.

**Estimated scope:** Variable. Pixel-based stub: ~40 lines. Full OCR: much more.

---

## Gap 6: Duplicate `load_json()` Across Files (MINOR)

**Problem:** `load_json()` is defined identically in **10 files**: `task_model.py`,
`scheduler.py`, `executor.py`, `locate.py`, `observe.py`, `pathfind.py`,
`calibrate.py`, `session.py`, `screenshot_mock.py`, `alas_command_inventory.py`.

**What's needed:** Extract to `scripts/utils.py` and import everywhere.

**Estimated scope:** 30 minutes (10 files to update + verify tests).

---

## Gap 7: Missing Task Definitions (DEFERRED)

**Problem:** `examples/azur-lane/tasks.json` has 11 tasks. `docs/workflows.md`
documents 26 workflows. Missing: Private Quarters, all 10 OpSi sub-workflows,
ShopFrequent/ShopOnce (as separate tasks), Shipyard, Freebies, Awaken,
Campaign, Ship Census, Ship Details, Formation Audit.

**Priority:** Deferred to Phase 6 (workflow piloting). The 11 existing tasks
cover the core daily loop. Missing tasks can be added as they're piloted.

---

## Gap 8: Emulator Startup + Game Login Is Not a Tool (BLOCKING for Phase 4)

**Problem:** Getting from "emulator not running" to "game at page_main" requires
10+ manual steps, each of which can fail independently. Here's what an agent
actually does today (observed 2026-03-19):

```
1. ADB connect → "device not found" (emulator crashed)
2. Check processes → MEmu not running
3. MEmuConsole start → wait 20s
4. ADB reconnect → works
5. ATX agent → "not responding on port 7912"
6. Reinitialize uiautomator2 via ALAS venv → works
7. Screenshot → black screen (Unity loading)
8. Wait 15s, screenshot → still black
9. Manually launch com.YoStarEN.AzurLane → loading screen
10. Wait 30s → splash screen "PRESS TO START"
11. Tap to start → announcements/popups
12. Dismiss popups → finally at page_main
```

Each step is a separate tool call where the agent guesses, waits, retries, and
often takes wrong turns. This is a **deterministic sequence** that should be a
single function call with detailed logging.

**What's needed:** A `scripts/emulator_startup.py` with one entry point:

```python
result = ensure_game_ready(
    emulator="memu",           # or "ldplayer", "bluestacks"
    serial="127.0.0.1:21513",
    package="com.YoStarEN.AzurLane",
    timeout=180,               # max seconds for full startup
    event_log=log,             # NDJSON logger
)
# result: {"success": True, "state": "page_main", "duration_s": 95}
```

### Phase 1: System-level emulator monitor (no ADB dependency)

Uses Win32 API, not ADB. Works even when ADB is broken.

1. **Window discovery + focus**: `ctypes` / `pywin32` to find emulator window
   by title/class (MEmu, LDPlayer, BlueStacks), bring to foreground, check
   if responding (`IsHungAppWindow`).

2. **System-level screenshot**: `mss` or `PIL.ImageGrab` to capture the emulator
   window directly from the Windows desktop compositor. This captures exactly
   what a human sees — bypasses ADB entirely.

3. **Emulator status classification** from system screenshot:
   - `not_found` — window doesn't exist
   - `not_responding` — window hung
   - `black_screen` — all/mostly black (Unity loading, normal for 30-120s)
   - `android_home` — emulator booted but game not started
   - `game_loading` — splash/loading screen visible
   - `game_title` — "PRESS TO START" screen
   - `game_running` — actual game UI visible
   - `crashed` — error dialog or crash reporter

4. **Dual-channel logging**: Every status check writes to NDJSON event log:
   timestamp, window handle/PID/title, status classification, system screenshot
   path, ADB status (connected/disconnected/error) for comparison, frame
   brightness/entropy (quantitative black screen detection).

### Phase 2: Full startup sequence (deterministic, logged)

The `ensure_game_ready()` function runs this state machine:

```
[check_emulator]
  → not_found  → start_emulator() → poll until window appears
  → not_responding → kill + restart
  → found → [check_adb]

[check_adb]
  → disconnected → adb connect, retry 3x
  → connected → [check_atx_agent]

[check_atx_agent]
  → not_responding → reinit uiautomator2 (via ALAS venv python -m uiautomator2 init)
  → responding → [check_game]

[check_game]
  → not_running → adb shell am start -n {package}/.SplashActivity
  → black_screen → poll system screenshot every 5s, log each frame
  → loading → wait, poll
  → title_screen → tap center, wait
  → announcements → dismiss popups (tap X, up to 5 rounds)
  → page_main → DONE, return success
  → unknown → escalate to agent
```

Every transition is logged. Every screenshot is saved. Every failure is
retried with backoff. The agent never has to guess.

### Phase 3: Integration with daemon

The daemon loop (Gap 1) calls `ensure_game_ready()` as its first step,
and again whenever the `restart` error strategy fires. The restart task
in `tasks.json` becomes a thin wrapper around this function.

**Why this matters:** Startup is the #1 failure point. Every session hits it.
An agent fumbling through 10 manual steps with ADB errors and black screens
wastes 5-10 minutes and often fails. A deterministic startup tool with
system-level observation makes startup a 60-90 second automated operation.

**Dependencies:** `pywin32` or `ctypes` (Win32 API), `mss` (fast screenshots).

**Estimated scope:** ~300 lines for the full startup tool + ~80 lines for tests.

---

## Gap 9: Executor Real Backend Is Completely Broken (BLOCKING for Phase 4)

**Problem:** `executor.py`'s `default_backend()` has **4 distinct bugs** that
make it non-functional. Every `_*_real` function will crash at runtime. These
bugs are masked because all tests use `mock_backend()` and the lazy imports
(inside function bodies) are never exercised.

**Bug 1 — `_navigate_real` (line 296):** Imports `find_path` but the function
in `pathfind.py` is named `pathfind`. Straight `ImportError`. Also reads
`result["path"]` but the actual key is `result["route"]`.

**Bug 2 — `_tap_real` (line 322):** Calls `tap(coords[0], coords[1])` but
`adb_bridge.tap` signature is `tap(serial: str, x: int, y: int)`. The x
coordinate gets passed as the serial string. Will fail at runtime.

**Bug 3 — `_swipe_real` (line 338):** Same missing `serial` parameter as tap.

**Bug 4 — `_locate_real` (line 351):** Imports `observe` from `observe.py` but
the actual function is named `build_observations`. Straight `ImportError`.

**Additionally:**
- `_navigate_real()` returns `{"success": True}` after taps **without calling
  `locate()` to verify arrival**. Blind navigation.
- MEmu uses DirectX rendering → `adb screencap -p` returns blank. The only
  working screenshot path is DroidCast via `pilot_bridge.py`.
- `pilot_bridge.py` is untracked (`??`), has zero tests, not in pyproject.toml.

**What's needed:**
1. Fix all 4 bugs in `default_backend()` (or replace with PilotBridge backend)
2. Add `serial` parameter plumbing (from config or constant)
3. Add arrival verification: `locate()` after navigation taps
4. Add at least one test that instantiates `default_backend()` to catch import errors
5. Decide: fix adb_bridge backend OR replace with PilotBridge backend for MEmu
6. Commit `pilot_bridge.py` with tests, add deps to pyproject.toml

**DroidCast timing caveat:** Each screenshot via `pilot_bridge.py` takes ~3
seconds (kill→start→port-forward→capture). The `_wait_until_state()` polling
loop with `poll_interval=2.0` will actually take ~5 seconds per iteration.
Timeout calculations will be wrong unless this is accounted for.

**Estimated scope:** ~80 lines to fix backend, ~100 lines for pilot_bridge tests.

---

## Gap 10: Phantom References in Documentation (MINOR)

**Problem:** `docs/architecture.md` references files that don't exist:
- `references/explorer.md`, `references/consolidator.md`,
  `references/optimizer.md` — the actual files are at `agents/*.md`
- `references/troubleshooting.md` — doesn't exist anywhere
- `assets/templates/graph-template.json` — neither directory nor file exists
- `data_collector.py` — referenced but not created (acknowledged as Phase 7)
- `examples/azur-lane/resources.json` — no resource store example exists

**What's needed:** Either create the files or update architecture.md to point
to where things actually live.

**Estimated scope:** 30 minutes.

---

## Gap 11: No Circuit Breaker or Re-locate on Startup (IMPORTANT)

**Problem:** Two edge cases that will cause infinite loops or immediate failure:

1. **No circuit breaker**: If `error_strategy: "restart"` fires and the restart
   also fails, the loop cycles `restart → task → fail → restart → task → fail`
   indefinitely. ALAS solves this with `GameTooManyClickError` (20 clicks / 60
   seconds threshold). We need equivalent bounds.

2. **No re-locate on startup**: When the daemon starts (or restarts after crash),
   `session.current_state` is `None`. The executor returns
   `{"success": False, "error": "Current state unknown"}` for any task with an
   `entry_state`. The daemon must screenshot + `locate()` to establish position
   before entering the main loop.

3. **Manifest staleness**: If `tasks.json` is edited externally (agent adjusts
   priorities), the daemon works with a stale in-memory copy. Need either
   file-watch reload or periodic re-read.

**What's needed:**
- Circuit breaker: max 3 consecutive failures for same task → disable task,
  max 5 restarts per hour → escalate to agent
- Re-locate step at daemon startup
- Periodic manifest reload (every cycle, or on file change)

**Estimated scope:** ~40 lines.

---

## Gap 12: Runtime Modules Never Imported (FRAGMENTATION)

**Problem:** Dependency analysis shows `task_model.py`, `resource_model.py`, and
`scheduler.py` are **never imported** by any other script. They're standalone CLI
tools that work in isolation but aren't wired into the execution pipeline.
`executor.py` imports `pathfind`, `adb_bridge`, `locate`, `observe`, and
`session` — but NOT `scheduler` or `task_model` or `resource_model`.

**What this means:** There's no code path where the scheduler picks a task and
hands it to the executor. The daemon loop (Gap 1) is the missing glue, but
even `executor.py` should probably import `task_model` for validation.

**What's needed:** The daemon loop (Gap 1) naturally solves this by importing all
three. But also consider whether `executor.py` should validate task definitions
via `task_model.validate_task_manifest()` before executing.

---

## Gap 13: No Agent Control Surface API (IMPORTANT)

**Problem:** The updated docs (`NORTH_STAR.md`, `architecture.md`, `plan.md`,
`CLAUDE.md`) all describe a three-tier agent control surface:

```
Tier 1: execute_task("commission"), navigate_to("page_dorm"), ensure_game_ready()
Tier 2: where_am_i(), why_did_last_transition_fail(), show_recent_failures()
Tier 3: Escalation payloads (screenshot + candidates + actions + recovery)
```

**None of these exist as callable functions.** Today, an agent interacting with
the runtime must manually import scheduler, executor, session, locate, and
stitch them together. The docs say the agent should never do this in normal
operation.

**What's needed:** A `scripts/runtime_api.py` that provides the clean
agent-facing surface:

```python
# Tier 1 — high-level runtime calls
def execute_task(task_id, manifest, graph, backend) -> dict
def navigate_to(target_state, graph, session, backend) -> dict
def ensure_game_ready(config) -> dict       # wraps emulator_startup.py

# Tier 2 — supervisory queries
def where_am_i(graph, backend) -> dict      # screenshot + locate, one call
def why_did_last_transition_fail(event_log) -> dict
def show_recent_failures(event_log, n=5) -> list

# Tier 3 — escalation payload construction
def build_escalation_payload(event_log, screenshot, candidates) -> dict
```

The Tier 1 functions wrap executor.py, pathfind.py, and emulator_startup.py.
The Tier 2 functions wrap locate.py and event log queries.
The Tier 3 function packages context for the agent when the runtime escalates.

**Build incrementally:**
- `where_am_i()` and `navigate_to()` can ship with steps 4-6
- `execute_task()` wrapping ships with step 10 (daemon)
- `ensure_game_ready()` ships with step 9 (emulator startup)
- Tier 2 queries ship after step 7 (event logging wired)
- Tier 3 escalation ships with step 10 (daemon escalation hooks)

**Estimated scope:** ~150 lines. Thin wrappers, not new logic.

---

## Gap 14: Data Collection Layer (DEFERRED)

**Problem:** `docs/architecture.md` describes Layer 4.5 (data collection with
pagination, census jobs, checkpoint/resume). No `data_collector.py` exists.

**Priority:** Deferred to Phase 7 per plan.md. Not needed for Phase 4.

---

## Forward Plan

### Execution Order (dependency-sequenced)

Reviewed and resequenced based on hidden dependencies. Each step unblocks
the next. Steps that can run in parallel are noted.

| Order | Work Item | Gap | Why this order |
|-------|-----------|-----|----------------|
| 1 | Extract `load_json()` to `scripts/utils.py`, update 10 files | Gap 6 | Prevents merge conflicts with all later changes |
| 2 | Fix 4 broken imports in executor.py `default_backend()` | Gap 9 | Unblocks everything — without this, zero tooling works live |
| 3 | Integration test: instantiate `default_backend()` + scheduler→executor round-trip | Gap 12 | Verify step 2 worked, catch future wiring breaks |
| 4 | Add `locate_validate` CLI mode to locate.py (`--screenshot` flag) | — | Phase 4 calibration tool. Lets the exploring agent validate state classification on every screenshot. NOTE: this is a debug/exploration tool per the updated docs, not the steady-state interface |
| 5 | Wire PilotBridge as executor backend (`pilot_backend()`) | Gap 9 | Can parallel with step 4. adb_bridge returns blank on MEmu; PilotBridge is the only working path. Backend must own screenshot capture internally per updated architecture |
| 6 | Add arrival verification to `_navigate_real()` — call locate() after taps | Gap 9 | Depends on working locate (step 4). No more blind navigation |
| 7 | Wire `execution_event_log.py` into executor and scheduler | Gap 4 | Do before daemon so daemon can log from day one. Per updated docs: "Event logging happens inside the runtime, not as a manual afterthought" |
| 8 | Add `page_hq` to graph.json + fix `page_dormevent` task/graph mismatch | Gap 10 | Content change, not structural. Can parallel with step 7 |
| 9 | Build `scripts/emulator_startup.py` — `ensure_game_ready()` | Gap 8, 13 | First Tier 1 control surface function. Can build/test independently |
| 10 | Build `scripts/daemon.py` — main loop, error_strategy, circuit breaker, SIGINT | Gap 1, 2, 11 | Depends on all above (working executor, backends, logging, graph) |
| 11 | Build `scripts/runtime_api.py` — agent control surface | Gap 13 | Wraps steps 4-10 into the three-tier API the docs describe. Built incrementally as each underlying piece ships |

**API decisions needed before step 2:**
- Where does `serial` come from? Options: `graph["metadata"]`, executor config
  dict, `PilotBridge.__init__` default. Must not conflict between backends.
- `run_id` for event logging: generated per daemon cycle or per task execution?

**Parallelizable pairs:** Steps 4+5 can run concurrently. Steps 7+8 can run
concurrently. Step 9 can run any time after step 5. Step 11 is built
incrementally — `where_am_i()` and `navigate_to()` ship with steps 4-6,
`ensure_game_ready()` ships with step 9, `execute_task()` ships with step 10,
Tier 2 queries ship after step 7.

### Phase 4 proper (live piloting)

After the above glue code exists:

1. Wire PilotBridge (DroidCast) as executor backend for MEmu
2. Validate `locate.py` against live emulator screenshots
3. Recalibrate anchors with `calibrate.py` using live data
4. Run navigation loops: `page_main` → each major page → `page_main`
5. Record every attempt in NDJSON event log
6. Fix anchor/path failures iteratively until >90% success rate
7. Verify arrival after every navigation (locate after tap sequence)

### Phase 5-10 (unchanged from plan.md)

The existing `plan.md` phases 5-10 remain valid:
- Phase 5: Vision-agent fallback
- Phase 6: Workflow piloting (execute full tasks end-to-end)
- Phase 7: Data collection + ship census
- Phase 8: Full daemon (4+ hours autonomous)
- Phase 9: Agent supervision protocol
- Phase 10: Progressive optimization

---

## Subagent Dispatch for Immediate Work

| Agent | Task | Deliverable |
|-------|------|-------------|
| Executor | Create `scripts/daemon.py` — main loop, error_strategy, circuit breaker, escalation, re-locate, manifest reload, SIGINT | Working daemon with tests |
| Executor | Create `scripts/emulator_startup.py` — Win32 window focus, system screenshot, status classification, ADB/ATX init, game launch, popup dismiss, full startup state machine | Working startup tool with tests |
| Executor | Rewire `executor.py` default_backend to PilotBridge + add arrival verification via locate() after navigation | Instrumented executor |
| Executor | Wire `execution_event_log.py` into executor + scheduler (task_start, task_complete, state_change, error events) | Event-traced runtime |
| Simplifier | Extract `load_json()` to `scripts/utils.py`, update all 10 files | No duplication |
| Test engineer | scheduler→executor integration test, wait_until/conditional/assert_state coverage, pilot_bridge mocked tests | test_integration.py expanded |
| Verifier | Run full test suite, check nothing broke | Green CI report |

---

## Edge Cases to Handle

From analyst review — the daemon loop must handle these:

| Edge Case | Risk | Mitigation |
|-----------|------|------------|
| All tasks waiting, none ready | Busy-spin | Sleep until `next_wakeup()`, cap at 5 min if None |
| Task fails repeatedly | Infinite restart loop | Circuit breaker: 3 consecutive failures → disable task, 5 restarts/hour → escalate |
| Session state unknown on startup | Every task fails immediately | Re-locate step before entering main loop |
| Manifest edited while daemon runs | Stale priorities | Reload manifest from disk each cycle |
| DroidCast 3s screenshot cycle | Polling timeouts wrong | Account for screenshot latency in `wait_until` timeout calculations |
| Two tasks ready simultaneously | Second task stale-waits | Handled by pick_next priority; second task runs next cycle |

---

## Test Priorities (from test engineer audit)

336 existing tests across 25 files. Key gaps:

| Priority | Gap | Risk |
|----------|-----|------|
| P1 | `pilot_bridge.py` — zero tests, the only working MEmu bridge | High |
| P2 | `executor.py` `wait_until` — polling loop entirely untested | High |
| P3 | scheduler→executor integration — no end-to-end test | High |
| P4 | `conditional` action type — untested | Medium |
| P5 | `assert_state` success path — only failure tested | Medium |
| P6 | `save_tasks` — write-to-disk not tested | Medium |
| P7 | `scheduler.py` CLI `main()` — not tested | Medium |

---

## Success Criteria

After this consolidation:

1. `python scripts/daemon.py --tasks examples/azur-lane/tasks.json --graph examples/azur-lane/graph.json --dry-run` shows the daemon loop picking tasks in priority order and simulating execution
2. `python scripts/daemon.py --tasks ... --graph ... --mock --iterations 5` runs the full mock loop for 5 cycles with error handling, circuit breaker, and event logging
3. `python scripts/emulator_startup.py --emulator memu --dry-run` shows the startup state machine steps with status classification
4. Event log captures every task start, complete, fail, state change, and escalation
5. All existing 273+ tests still pass
6. New integration tests cover scheduler→executor→session round-trip
7. Error strategies (retry, restart, skip, escalate) are exercised in tests
8. Circuit breaker triggers after repeated failures in tests
9. Executor verifies arrival via `locate()` after every navigation (not blind)
10. `pilot_bridge.py` has tests and is committed
11. Agent control surface API exists (`runtime_api.py`) with at minimum:
    - `where_am_i()` — one-call state classification (screenshot + locate)
    - `navigate_to(target)` — one-call navigation with arrival verification
    - `ensure_game_ready()` — full startup-to-login
    - `execute_task(task_id)` — full task execution via scheduler+executor
12. An agent session can use the Tier 1 calls instead of raw `PilotBridge.tap()` for normal operations, with direct tooling reserved for exploration and debugging
