# Architecture: Capability-to-Layer Mapping

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

## Layer Dependency Chain

```
Layer 0 (existing libs)
  └── pytransitions, Playwright/ADB/etc., SCXML semantics
       │
Layer 1 (schema extensions)
  └── Extends graph definition format with anchors, costs, wait states, thresholds
       │
Layer 2 (runtime tools)
  └── locate.py, pathfind.py, session.py, screenshot_mock.py, adb_bridge.py, observe.py, calibrate.py
  └── These consume Layer 1 schema, call Layer 0 for graph introspection
       │
Layer 3 (SKILL.md playbook)
  └── Tells the agent how and when to use Layer 2 tools
  └── Progressive disclosure to Layer 4
       │
Layer 4 (agent role references)
  └── Deep instructions per phase, loaded on demand
```

The agent reads SKILL.md (Layer 3), which tells it to call scripts (Layer 2), which operate on the extended graph format (Layer 1), which is built on top of existing state machine libraries (Layer 0).
