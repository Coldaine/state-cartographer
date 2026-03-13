---
name: state-graph-navigation
description: Use an existing state graph to navigate external systems cheaply. Covers locate, pathfind, and session management.
---

# State Graph Navigation

## Overview

Once a state graph exists (built via the `state-graph-authoring` skill), this skill lets you use it for cheap, deterministic navigation. Instead of taking screenshots and reasoning about UI, you query the graph.

## Core Workflow

### 1. Orient: Where Am I?

```bash
python plugin/scripts/locate.py --graph graph.json --session session.json
```

Returns your current state with confidence score. Uses cheap anchor checks (DOM selectors, window titles, process focus) — no vision required for most states.

### 2. Plan: How Do I Get There?

```bash
python plugin/scripts/pathfind.py --graph graph.json --from current_state --to target_state
```

Returns the cheapest route (sequence of transitions) from current state to target. Uses Dijkstra's algorithm over transition costs. Prefers deterministic transitions over vision-required ones.

Options:
- `--avoid state_name` — exclude states from routing (e.g., avoid irreversible states)
- `--prefer-deterministic` — penalize vision-required transitions

### 3. Execute: Follow the Route

For each transition in the route:
1. Execute the transition action (deterministic or vision-based)
2. After each step, call `locate()` to confirm you arrived at the expected state
3. If confirmation fails, re-plan from current position

### 4. Track: Maintain Session

```bash
python plugin/scripts/session.py confirm --state state_name --session session.json
python plugin/scripts/session.py transition --event event_name --session session.json
```

Session history enables cheaper orientation on subsequent `locate()` calls.

## When Navigation Fails

- **locate() returns unknown state** → See `rules/orientation.md` for recovery
- **Transition doesn't work** → Try fallback action if available, else re-plan
- **Route is blocked** → Re-plan with `--avoid` for the blocked state
- **Confidence too low** → See `rules/safety.md` for escalation

## Reference

- `scripts/locate.py` — passive state classifier
- `scripts/pathfind.py` — weighted route planner
- `scripts/session.py` — session state manager
- `scripts/graph_utils.py` — graph inspection utilities
