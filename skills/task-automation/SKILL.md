---
name: task-automation
description: Define, schedule, and execute automated tasks against an external system. The tooling runs the loop; the agent supervises.
---

# Task Automation

## Overview

This skill covers the full automation lifecycle: defining tasks, scheduling them, executing them, and supervising the process. Navigation (`state-graph-navigation`) is a subroutine used by the executor — you rarely call it directly.

## Prerequisites

- A validated state graph (`graph.json`) for the target system
- A live connection (ADB, Playwright, etc.) or mock backend for testing

## The Automation Loop

```
1. scheduler.pick_next(tasks, now, resources)  → which task to run
2. executor.execute_task(task, graph, session)  → navigate + run actions
3. resource_model.update(observations)          → track game state
4. scheduler.compute_next_run(task)             → when to run again
5. If error → task's error_strategy (retry, restart, skip)
6. If unknown state → escalate to agent
7. Loop
```

The tooling handles steps 1-5 autonomously. You (the agent) handle step 6 and overall supervision.

---

## Phase 1: Define Tasks

Create `tasks.json` alongside the state graph:

```bash
# Validate task definitions
python scripts/task_model.py --tasks examples/azur-lane/tasks.json --validate
```

Each task needs:
- **entry_state**: which screen to navigate to (must exist in graph.json)
- **schedule**: when to run — `interval` (every N minutes), `server_reset` (daily), `one_shot`, `manual`
- **actions**: what to do once there — list of tap/swipe/wait/navigate/assert steps
- **error_strategy**: what to do on failure — `retry`, `restart`, `skip`

### Task definition example:

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

### Action types:

| Action | Required fields | Description |
|--------|----------------|-------------|
| `navigate` | `target` | Navigate to a state via pathfind |
| `tap` | `x`, `y` | Tap screen coordinates |
| `swipe` | `x1`, `y1`, `x2`, `y2`, `duration` | Swipe gesture |
| `wait` | `seconds` | Sleep for duration |
| `wait_until` | `target_state`, `timeout` | Poll locate() until state reached |
| `assert_state` | `expected` | Verify current state matches |
| `read_resource` | `name`, `region` | Read a value from screen |
| `conditional` | `condition`, `then`, `else` | Branching logic |
| `repeat` | `count`, `body` | Loop a sub-sequence N times |

---

## Phase 2: Configure Resources

Set up resource tracking for threshold-gated tasks:

```python
from scripts.resource_model import create_store, set_resource, save_store

store = create_store()
set_resource(store, "oil", 8500, source="ocr")
set_resource(store, "coins", 42000, source="ocr")
save_store(store, "resources.json")
```

Tasks can declare resource requirements:
```json
"requires": { "oil": { "min": 200 } }
```

The scheduler checks these before marking a task as ready.

---

## Phase 3: Review the Schedule

```bash
# See what's ready, waiting, and disabled
python scripts/scheduler.py --tasks tasks.json --resources resources.json --dry-run
```

Output shows:
- **Ready tasks** — can run now (enabled + due + resources met)
- **Waiting tasks** — enabled but not yet due, sorted by next_run
- **Disabled tasks** — skipped

Adjust by editing tasks.json: change `enabled`, `schedule`, or priority ordering.

---

## Phase 4: Run Tasks

### Single task (testing/debugging):
```bash
python scripts/executor.py --task commission --graph graph.json --tasks tasks.json --mock
```

### Scheduled loop (production):
```python
from scripts.scheduler import pick_next, compute_next_run
from scripts.executor import execute_task
from scripts.task_model import load_tasks, set_next_run

manifest = load_tasks("tasks.json")
graph = load_json("graph.json")

while True:
    task_id, task_def = pick_next(manifest, now(), resources)
    if task_id is None:
        sleep_until(next_wakeup(manifest, now()))
        continue
    
    result = execute_task(task_def, graph, session, backend)
    if result["success"]:
        next_run = compute_next_run(task_def, now())
        set_next_run(manifest, task_id, next_run)
    else:
        handle_error(task_def, result)
```

---

## Phase 5: Supervise

Your role as the agent:

### Before the loop
- Review `scheduler --dry-run` output
- Enable/disable tasks based on current goals
- Adjust priorities if needed

### During the loop
- You're called when the executor encounters:
  - Unknown state (not in graph)
  - Unexpected popup or dialog
  - Resource decision requiring judgment
  - Repeated task failures

### Between sessions
- Review error logs
- Update graph.json if the external system changed
- Add new tasks discovered during play
- Recalibrate anchors if mismatches detected

### Planning
- Check timer expirations: "Commission finishes in 15 min, research in 42 min — collect commission first"
- Review resource levels: "Oil at 200, too low for campaign farming — switch to low-oil tasks"
- Adjust schedule: "Event ending tomorrow — prioritize event tasks"

---

## Reference

| Script | Purpose |
|--------|---------|
| `scripts/task_model.py` | Task definitions — load, validate, query |
| `scripts/resource_model.py` | Resource tracking — set, get, threshold checks, timers |
| `scripts/scheduler.py` | Scheduling — ready/waiting tasks, priority, next_run |
| `scripts/executor.py` | Execution — run task actions with auto state tracking |
| `scripts/locate.py` | State classification (called by executor) |
| `scripts/pathfind.py` | Route planning (called by executor) |
| `scripts/session.py` | Session history (called by executor) |
