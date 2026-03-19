# North Star

## The Problem

When an AI agent automates an external system — a mobile game, a web app, a desktop application — it needs to do two fundamentally different things:

1. **Navigate**: get to the right screen
2. **Act**: execute a sequence of domain-specific operations (collect rewards, dispatch commissions, buy items, run battles)

Most automation tooling stops at navigation. "Where am I?" and "How do I get there?" are solved, and then the agent is left to figure out everything else from scratch: what tasks exist, when they should run, what resources are available, what to do when something fails. The agent spends its most powerful capability (general intelligence) on work that should be deterministic and schedulable.

The deeper problem is that navigation is only ~10% of real automation. The other 90% is scheduling, resource tracking, decision-making, and error recovery. An automation framework that only solves navigation is like a car with a steering wheel but no engine.

## The Insight

Real automation systems (like AzurLaneAutoScript, which automates Azur Lane across 43 screens) are **task schedulers with navigation as a subroutine**. ALAS's architecture:

```
FOREVER:
  task = get_next_task(priority + NextRun timestamps)
  navigate_to(task.entry_screen)      ← navigation (~10% of code)
  execute_task_actions(task)           ← domain logic (~80% of code)
  update_resources(observed_values)
  set_task_next_run(schedule_rule)
  if error → inject recovery task
```

Navigation is essential but it's not the main event. The main event is the **task loop**: what runs, when, with what resources, and what happens when it fails.

If you build both the navigation layer AND the task execution layer, the LLM agent becomes a **supervisor** instead of a manual operator. The tooling plays the game. The agent watches, plans, and intervenes only when something unexpected happens.

## The Vision

State Cartographer is an **automation runtime** for external systems. It enables an AI agent to:

- **Map** an unfamiliar system into a queryable state graph (screens, transitions, anchors)
- **Navigate** between any two states deterministically, without vision reasoning
- **Define tasks** as schedulable units of work (entry state + action sequence + schedule + error handling)
- **Schedule** tasks automatically based on priority, timing, and resource constraints
- **Execute** task action sequences with automatic state tracking and error recovery
- **Track resources** (currencies, timers, capacities) as a cache of observed values
- **Supervise** via LLM agent only for genuine ambiguity, planning, and anomaly handling

The end state: the tooling runs the automation loop autonomously. The agent is called when the tooling encounters something it can't handle.

## Agent Control Surface

The runtime should present a supervisory control surface to the agent. In normal operation, the agent should not have to manually request screenshots before every action or manually stitch together raw taps into a workflow.

The intended interaction levels are:

1. **High-level runtime calls**
   `execute_task("commission")`
   `navigate_to("page_dorm")`
   `ensure_game_ready()`
2. **Supervisory queries**
   `where_am_i()`
   `why_did_last_transition_fail()`
   `show_recent_failures()`
3. **Escalation payloads pushed up by the runtime**
   screenshot attached
   current candidates
   last N actions
   proposed recovery paths

This implies a clear ownership boundary:

- Screenshot capture belongs to the runtime/backend, not to the agent's normal control loop
- The executor/daemon captures screenshots internally for `locate`, arrival verification, recovery, and event logging
- Direct screenshot calls remain valid for debugging, calibration, and exploration, but they are not the steady-state operating model

## Goals

### 1. The tooling should play the game most of the time

Known task sequences (collect rewards, dispatch commissions, run dailies) execute automatically without LLM involvement. The scheduler picks the next task, the executor runs it, resources are updated, and the next run is scheduled.

### 2. The agent should supervise, not operate

The agent reviews the schedule, adjusts priorities, enables/disables tasks, and handles exceptions. It does NOT manually call `session.py confirm` after every tap or manually ask for a screenshot before every state check. That happens automatically inside the executor/backend stack.

### 3. Navigation should be cheap and deterministic

Given a state graph with anchors, `locate()` cheaply determines the current state and `pathfind()` returns the optimal route. No LLM reasoning for the common case. When deterministic navigation fails, the vision agent takes over — and every pattern handled by vision that repeats 3+ times gets promoted to a deterministic entry in the graph.

### 4. Recovery should be automatic for known errors

When a task fails with a known error pattern, the scheduler injects a recovery task (restart, return to main menu) and retries. The agent is only escalated for genuinely unknown situations.

### 5. Resource awareness should gate task execution

The scheduler checks resource requirements before running a task ("don't farm if oil < 200"). Resources are observed from the game UI, not computed.

### 6. Data collection should be a first-class operation

The system must be able to inventory the entire dock (400+ ships), read individual ship stats/equipment/skills, record fleet formations, and snapshot resource levels. This requires a separate data collection scheduler with pagination support, interruptibility, and resumption from checkpoints.

### 7. Recording captures everything

Every action during live piloting — every screenshot, every tap, every state transition, every OCR read — is recorded in an append-only NDJSON event log. This corpus enables replay, debugging, anchor recalibration, and progressive optimization.

### 8. The system should be buildable incrementally

Start with the graph (navigation). Add task definitions. Add scheduling. Add resource tracking. Add data collection. Each layer works independently and adds value on its own, but the full stack is where the real power lives.

### 9. The methodology should be teachable to an LLM

The full process — from exploration through task definition, scheduling, data collection, and supervision — should be captured as a playbook an LLM can follow.

## What This Is Not

- **Not another agent orchestration framework.** LangGraph, CrewAI, and similar tools manage the agent's own workflow. State Cartographer models and automates the *external system*.
- **Not an ALAS fork.** ALAS is the reference implementation we learn from and an optional source of labeled observations. State Cartographer generalizes the pattern to any external system, not just Azur Lane, and should not depend on ALAS as its live control plane.
- **Not a browser/mobile automation tool.** Playwright, ADB, and Appium are action backends. They execute transitions. The runtime logic lives above them.

## Open Questions

**Data collection at scale.** Paging through 400+ ships in the dock, reading stats/equipment/skills for each one — the pagination engine needs to be robust, interruptible, and resumable. How do we handle OCR errors mid-census? How do we detect we've scrolled past the end?

**Resource observation.** OCR-based resource reading is fragile. The right abstraction combines dedicated screen regions, color-based status detection, and template matching. Different data types need different methods (numbers via OCR, status via color, icons via template match).

**Vision agent integration.** When deterministic navigation fails, the vision agent must take over seamlessly. The handoff protocol — when to escalate, what context to pass, how to incorporate the agent's recovery action back into the graph — needs to be tight.

**Gesture recording and replay.** Swipes through the dock, map panning in OpSi, pinch-to-zoom — these gestures need to be recorded as parameterized actions (start, end, duration) and replayable.

**Decision engine depth.** Simple threshold gating ("oil >= 200") is implemented. Complex decisions ("which of 4 commissions to accept based on rewards vs. duration") need a strategy. The agent brings judgment; the tooling brings speed.

**Progressive determinism.** Every time the vision agent handles a new case, the system should learn from it. After 3 repeats of the same pattern, it becomes a deterministic handler. The goal is to shrink the vision-required set to <5% of all operations.

**Multi-account / multi-server.** ALAS supports per-account configuration. The task model should support this but the scope isn't defined yet.

## Guiding Principles

**The tooling does the work; the agent does the thinking.** Deterministic operations (navigation, task execution, screenshot capture, state verification, scheduling) are handled by the runtime. LLM reasoning is reserved for planning, anomaly detection, and judgment calls.

**The graph is infrastructure, not the product.** The graph enables navigation, which enables task execution, which enables automation. The graph by itself is necessary but not sufficient.

**Existing tools are allies.** We build on ADB, Playwright, pytransitions, and whatever the user already has. We don't reimplement solved problems.

**The human stays in the loop for judgment, not for labor.** The agent supervises. The human provides domain knowledge and makes calls that require understanding intent or consequence.

## Reference Case

ALAS (AzurLaneAutoScript) is the existence proof. Over 9 years, it built a 43-state page graph for Azur Lane with color-based anchors, BFS pathfinding, deterministic transitions, and recovery from unknown states. Every problem State Cartographer addresses — state detection, cheap navigation, orientation, progressive optimization — ALAS solved by hand for one specific system.

State Cartographer exists because that manual process should be a playbook, not a heroic engineering effort. The ALAS page graph (`module/ui/page.py`, `module/ui/assets.py`, `module/ui/ui.py`) is the canonical reference for validating our schema, tools, and methodology against a real, battle-tested system.
