---
name: state-graph-navigation
description: Navigate external systems using a state graph. Used as a subroutine by the task executor, or directly by the agent for ad-hoc navigation.
---

# State Graph Navigation

## Overview

Navigation is a **subroutine** within the automation runtime, not the top-level workflow. The task executor (`scripts/executor.py`) calls navigation automatically when entering a task's entry state. You only use these tools directly for ad-hoc navigation or debugging.

For the full automation workflow, see `skills/task-automation/SKILL.md`.

## Core Tools

### 1. Orient: Where Am I?

```bash
python scripts/locate.py --graph graph.json --session session.json
```

Returns current state with confidence score. Uses cheap anchor checks — no vision for most states.

### 2. Plan: How Do I Get There?

```bash
python scripts/pathfind.py --graph graph.json --from current_state --to target_state
```

Returns cheapest route (Dijkstra over transition costs). Options:
- `--avoid state_name` — exclude states from routing
- `--prefer-deterministic` — penalize vision transitions

### 3. Execute: Follow the Route

For each transition in the route:
1. Execute the transition action
2. Call `locate()` to confirm you arrived
3. If confirmation fails, re-plan from current position

**Note:** The executor does this automatically. You only do this manually for ad-hoc navigation.

### 4. Track: Maintain Session

```bash
python scripts/session.py confirm --state state_name --session session.json
```

**Note:** The executor calls `session.confirm` automatically after every state change. You only call this manually during exploration or debugging.

## When Navigation Fails

- **locate() returns unknown state** → See `rules/orientation.md` for recovery
- **Transition doesn't work** → Try fallback action if available, else re-plan
- **Route is blocked** → Re-plan with `--avoid` for the blocked state
- **Confidence too low** → See `rules/safety.md` for escalation

## Reference

- `scripts/locate.py` — passive state classifier
- `scripts/pathfind.py` — weighted route planner
- `scripts/session.py` — session state manager
- `scripts/executor.py` — task executor (calls navigation automatically)
- `scripts/graph_utils.py` — graph inspection utilities
