---
name: state-graph-authoring
description: Systematic methodology for building, validating, and refining state graphs of external systems. Covers exploration, consolidation, optimization, and maintenance.
---

# State Graph Authoring Playbook

## Overview

State Graph Authoring is the core methodology for building, maintaining, and iteratively improving queryable state graphs of external systems. A state graph is a complete model of a system's observable states and the transitions between them, annotated with cheap confirmation signals (anchors) and cost profiles. This skill transforms an unfamiliar system into an API-like structure: you ask "where am I?" and "how do I get to X?", and the graph gives deterministic, cheap answers.

**When to use this skill:**
- Initial mapping of a new external system (web app, mobile game, desktop application, CLI tool)
- Refining an existing graph (discovering new states, improving anchors, replacing transitions)
- Validating a graph against live behavior
- Transitioning a system from vision-heavy to deterministic navigation

**What you're not doing:**
- Writing one-off automation scripts. This is not a quick solution tool; it's an infrastructure-building tool.
- General-purpose agent orchestration. The graph models the external system, not the agent's reasoning.
- Building state machines for your own application. This models systems you don't control.

## Quick Orientation: Where Are You in the Process?

Answer these three questions:

1. **Do you have a graph definition at all?**
   - No → start at **Phase 1: Exploration**
   - Yes → go to #2

2. **Is the graph complete for the system you're automating?**
   - Unsure or no → **Phase 2: Consolidation**
   - Yes, but hard to navigate → **Phase 3: Transition Replacement**
   - Yes, and most transitions are deterministic → **Phase 4: Orientation Layer**
   - Graph exists and you're using it → **Phase 6: Maintenance**

3. **Are you blocked or uncertain?**
   - I can't tell one state from another → **Phase 2, Anchor Identification**
   - Transitions take too long and cost too many tokens → **Phase 3**
   - I'm getting lost or can't reorient after changes → **Phase 5**
   - The graph used to work, now it doesn't → **Phase 6**

---

## Phase 1: Exploration

### Objective
Systematically navigate the target system and capture raw observations at each state. The output of exploration is a **dataset**: timestamped sequences of screenshots, actions, DOM dumps, and state labels. The graph definition is built from this dataset in Phase 2.

### Strategy

**Start from a known entry point.** Identify one state you can reliably reach:
- Home screen or main menu (web/desktop)
- App startup state (mobile)
- Initial landing state after login (SaaS)
- Any state that appears every session in the same way

Take a screenshot. Document what you see.

**Navigate deliberately, not randomly.** From your known state, pick one accessible transition. Execute it. Record:
- What you did (e.g., "clicked 'Settings' in nav menu")
- The result (e.g., "navigated to settings screen")
- New observations

**Build a breadth-first tree.**
- Level 0: entry state (main menu)
- Level 1: all states reachable from entry state (visit each one)
- Level 2: all states reachable from each Level 1 state
- Use this tree structure to ensure systematic coverage, not random wandering

**Use `mock.py capture` to record each state.**

```bash
python plugin/scripts/mock.py capture \
  --state main_menu \
  --screenshot screenshot.png \
  --notes "main menu, visible: nav menu, events banner, fleet status display"
```

### What to Record at Each State

For every distinct screen/state you reach, capture:

1. **Screenshot** (via `mock.py capture`)
2. **DOM dump or system state** (if accessible)
3. **Observation notes** (free-form, what you see)
4. **Action that got you here**: what did you do in the previous state to reach this one?
5. **Available transitions** (things you can do from here)

### Stop Condition: Convergence, Not Exhaustion

You don't need to visit every possible state. You need convergence: the point where you're discovering very few new states relative to effort.

Don't spend hours finding the rare states not in your critical paths. Those will emerge during maintenance when they occur in live usage.

### Pitfall: Mistaking Transient Content for State Changes

If the **underlying structure is identical** and only the **content changes**, it's the same state. The graph records structural identity, not content identity. Anchors will be chosen from the stable layer later.

### Going Offline: Mock Dataset

Once you've captured screenshots and observations, you have a complete offline dataset. You can now build the graph definition and anchors without needing the live system.

```bash
python plugin/scripts/mock.py validate --graph graph.json
python plugin/scripts/mock.py test-locate --graph graph.json --screenshot screenshot.png
```

This decouples exploration from development.

---

## Phase 2: Consolidation

### Objective
Transform raw observations into a clean, minimal state graph definition.

### Step 1: List All Observed States and Their Observations

Gather your captured screenshots and notes. For each unique screen you saw, create an entry with observations, notes, and transitions.

### Step 2: Identify State Boundaries

- If the navigation intent is identical across variations, they're the same state.
- If the **underlying structure is identical** and only the **content changes**, it's the same state.

### Step 3: Identify and Prioritize Anchors

An **anchor** is a cheap, stable signal that confirms "you are in this state."

**Cost hierarchy:**
1. **Cost 1 (nearly free):** DOM selectors, window titles, process focus, file existence
2. **Cost 2 (cheap):** Regex pattern matching on text, pixel color at coordinates
3. **Cost 3–5 (moderate):** Screenshot region hash, perceptual hash comparison
4. **Cost 5+ (expensive):** Full screenshot, vision model interpretation

**Rules for anchors:**
- Must be **stable across sessions** (no transient content)
- Must be **unique to this state**
- Prefer **structural elements** over content
- Prefer **negative anchors** for states that are temporary or transient

### Step 4: Create the Graph Definition (JSON)

See `references/schema.md` for complete schema.

### Step 5: Validation Checkpoint

```bash
python plugin/scripts/mock.py validate --graph graph.json
```

---

## Phase 3: Transition Replacement

### Objective
Replace expensive vision-driven transitions with cheap deterministic function calls.

For each transition in your graph:

1. **Is this a common UI pattern?** (back button, menu navigation, dialog confirm)
2. **Do I know the deterministic action?** (DOM selector, URL, keyboard shortcut)
3. **Is the transition fragile?** (depends on pixel coordinates, multiple similar buttons)

Update the graph with deterministic actions where possible. Mark fragile transitions with fallbacks.

---

## Phase 4: Wait State Identification

### Objective
Identify states where the system is doing autonomous work and annotate them for polling.

For each wait state, annotate:
- `expected_duration_ms`
- `poll_interval_ms`
- `exit_signals` (cheap checks for completion)
- `timeout_behavior`

---

## Phase 5: Orientation Layer

### Step 1: Passive State Classification (`locate()`)

```bash
python plugin/scripts/locate.py --graph graph.json --session session.json
```

### Step 2: Session Management

```bash
python plugin/scripts/session.py init --graph graph.json > session.json
python plugin/scripts/session.py confirm --state main_menu --session session.json
python plugin/scripts/session.py transition --event tap_dock --session session.json
```

### Step 3: Active Disambiguation

If `locate()` returns ambiguity, execute the suggested probing strategy. See `../../rules/orientation.md`.

---

## Phase 6: Maintenance

### Trigger: Something Goes Wrong

1. Take a screenshot and DOM dump
2. Check against the graph
3. Add new state or update existing anchors
4. Revalidate

```bash
python plugin/scripts/mock.py capture --state new_state_name --screenshot screenshot.png
python plugin/scripts/mock.py validate --graph graph.json
```

---

## Common Pitfalls

1. **Trying to Be Complete on First Pass** — Explore critical paths, fill gaps during maintenance
2. **Choosing Fragile Anchors** — Prefer structural anchors (DOM IDs, window class names)
3. **Confusing the Graph with the Task Automation** — The graph is infrastructure, not the automation itself
4. **Not Enough Wait State Annotation** — Annotate wait states to avoid wasting vision tokens
5. **Skipping Validation** — Always run `mock.py validate` after graph updates

---

## Reference Documents

- `references/schema.md` — complete schema specification
- `../../agents/explorer.md` — agent instructions for Phase 1
- `../../agents/consolidator.md` — agent instructions for Phase 2
- `../../agents/optimizer.md` — agent instructions for Phase 3

## Success Criteria

- [ ] `graph.json` covers all states involved in your automation task
- [ ] Each state has at least two anchors (one low-cost, one fallback)
- [ ] `mock.py validate` passes
- [ ] `locate()` reliably returns current state
- [ ] 80%+ transitions are deterministic (cost ≤ 5)
- [ ] All wait states are annotated with exit signals
- [ ] `pathfind()` routes between arbitrary states without vision reasoning
