# State Cartographer — Master Plan

## What This Is

State Cartographer is a Claude Code plugin for building queryable state graphs of external systems. It turns "take a screenshot, reason about pixels, click something" into "query the graph, get a deterministic action, execute it." The graph is infrastructure that makes AI automation of external systems progressively cheaper and more reliable.

## Current Status

**Phase: Phase 1 Foundation (Complete)**

**Reference case:** ALAS (AzurLaneAutoScript) serves as the primary validation target.
Its 43-page state graph with real color anchors and BFS navigation — built by hand
over 9 years — is the benchmark for whether our schema and tools can represent a
real-world system. ALAS is reference data, not a runtime dependency.

The project has been scaffolded and restructured as a proper Claude Code plugin:
- Core Python scripts (`locate.py`, `pathfind.py`, `session.py`, `graph_utils.py`, `schema_validator.py`, `screenshot_mock.py`)
- Plugin content (skills, agents, rules, commands) moved to root level (no more `plugin/` subdirectory)
- `pyproject.toml` replaces `requirements.txt`; UV for environment management, Ruff for linting
- Claude Code hooks (`hooks/hooks.json`, `hooks/post_write.py`)
- Plugin manifest (`.claude-plugin/plugin.json`)
- Test suite with fixtures — all tests passing
- CI pipeline (GitHub Actions, Python 3.11/3.12/3.13)
- Design documentation organized in `docs/`

---

## Development Phases

### Phase 1: Foundation — Make the Tests Pass

**Goal:** The 6 Python scripts work correctly against the test fixtures.

**Workflow:**
1. Run `pytest tests/ -v` — see what fails
2. Fix each script until its tests pass
3. Run `pytest tests/ --cov=scripts` — verify coverage
4. All 6 modules at 80%+ coverage

**What's being validated:**
- `locate.py` correctly classifies states from observation + graph + session data
- `pathfind.py` returns optimal routes via Dijkstra's algorithm
- `session.py` tracks state history correctly (init, confirm, transition, query)
- `graph_utils.py` inspects graphs (list states, reachable states, orphans, missing anchors)
- `schema_validator.py` catches invalid graph definitions
- `mock.py` captures screenshots and validates anchor coverage

**Exit criteria:** `pytest tests/ -v` passes, CI is green.

---

### Phase 2: Schema Validation — Lock Down the Data Format

**Goal:** The graph.json schema is precisely specified and the validator enforces it.

**Workflow:**
1. Write 5-10 more graph fixtures (edge cases: empty graphs, self-loops, disconnected components, deep hierarchies)
2. Write property tests for schema validation (any valid graph passes, any invalid graph fails with a specific error)
3. Document the schema completely in `skills/state-graph-authoring/references/schema.md`

**What's being validated:**
- Every field in the schema has a defined type, constraints, and default value
- The validator catches all known invalid patterns
- Error messages are actionable ("state 'dock' has anchor with invalid type 'magic'")

**Exit criteria:** Schema reference doc is complete. Validator has property tests. No ambiguity in what a valid graph looks like.

---

### Phase 3: Offline Simulation — End-to-End Without a Live System

**Goal:** Run the full authoring workflow (explore → consolidate → optimize → navigate) against mock data.

**Workflow:**
1. Create a realistic mock system in `examples/` (20+ states, 30+ transitions, mix of deterministic and vision-required)
2. Capture mock screenshots for each state
3. Run `locate.py` against mock screenshots — verify correct classification
4. Run `pathfind.py` — verify optimal routes
5. Run `session.py` — verify session tracking through a multi-step workflow
6. Run `mock.py validate` — verify anchor coverage

**What's being validated:**
- The tools work together as a pipeline
- The SKILL.md playbook is followable (an LLM can read it and execute the workflow)
- The graph schema supports all the annotation types needed for real systems

**Exit criteria:** A complete example in `examples/mock-system/` with graph, screenshots, and a walkthrough README.

---

### Phase 4: Environment Provider Interface

**Goal:** Define how the cartographer connects to external systems (ADB, Playwright, desktop accessibility).

**Workflow:**
1. Design the provider interface: what capabilities must a provider expose? (screenshot, DOM access, action execution, system state query)
2. Build a reference provider for one system (Playwright for web, or ADB for Android)
3. Wire `locate.py` to use the provider for live observation gathering
4. Wire transition execution to use the provider for action dispatch

**What's being validated:**
- The provider abstraction is simple enough to implement in an afternoon
- It's flexible enough to cover web, mobile, and desktop
- The tools work against a live system, not just mock data

**Open questions to resolve:**
- How does the user configure which provider to use?
- How are provider capabilities discovered (does the system support DOM? screenshots only?)
- How do we handle providers that need setup (Playwright browser launch, ADB device connection)?

**Exit criteria:** One working provider. `locate.py` runs against a live system and returns correct state.

---

### Phase 5: Live Exploration — An Agent Builds a Graph

**Goal:** An LLM agent follows the SKILL.md playbook and builds a state graph of a real system.

**Workflow:**
1. Pick a target system (a web app with 10-20 states)
2. Give Claude Code the `state-graph-authoring` skill
3. The agent follows the playbook: explores, captures, consolidates, validates
4. The human provides judgment calls at decision points (state boundaries, anchor stability)
5. The agent produces a working `graph.json`

**What's being validated:**
- The playbook is complete enough for an LLM to follow
- The tools support the full workflow (no missing capabilities)
- The agent/human handoff points are clear and well-defined
- The resulting graph actually works for navigation

**Exit criteria:** A real graph built by an agent, validated, and used for navigation on the target system.

---

### Phase 6: Progressive Optimization — The Graph Gets Cheaper

**Goal:** Demonstrate the vision-to-deterministic transition arc.

**Workflow:**
1. Start with a graph where most transitions are `vision_required`
2. Run the optimizer agent on the graph
3. Measure: what percentage of transitions became deterministic?
4. Run navigation sessions and measure: average cost per route drops over time
5. Introduce a simulated system update — verify the maintenance workflow catches the change

**What's being validated:**
- The optimization pass meaningfully reduces costs
- The maintenance workflow catches graph drift
- Session-over-session improvement is measurable

**Exit criteria:** Documented cost reduction from initial graph to optimized graph. At least one maintenance cycle demonstrated.

---

## Key Workflows

### Workflow: "I want to automate a new system"

```
1. Connect to the system (configure provider)
2. Start the state-graph-authoring skill
3. Follow Phase 1 (Exploration): systematic BFS, capture screenshots
4. Follow Phase 2 (Consolidation): collapse duplicates, choose anchors, build graph.json
5. Validate: mock.py validate
6. Follow Phase 3 (Optimization): replace vision transitions with deterministic
7. Navigate: use state-graph-navigation skill for cheap routing
8. Maintain: update graph when the system changes
```

### Workflow: "I'm lost and need to recover"

```
1. Call locate.py (passive classification)
2. If definitive → proceed
3. If ambiguous → execute suggested probes
4. If unknown → navigate to known state (back button, home, restart)
5. If still lost → escalate to human
```

### Workflow: "The system updated and my graph is broken"

```
1. locate() returns unknown or wrong state
2. Capture screenshot + observations
3. Diagnose: new state? broken anchor? changed transition?
4. Update graph.json
5. Revalidate: schema_validator.py + mock.py validate
6. Test affected routes
```

### Workflow: "I want to optimize an existing graph"

```
1. Run graph_utils.py summary — see current state
2. Identify vision-required transitions
3. For each: can it be replaced with a deterministic action?
4. Update transition actions and costs
5. Test against live system
6. Measure cost reduction
```

---

## Architecture Summary

```
Layer 4: Agent Roles (explorer, consolidator, optimizer)
Layer 3: Skill Playbooks (SKILL.md — the methodology)
Layer 2: Runtime Tools (locate, pathfind, session, graph_utils, mock, validator)
Layer 1: Schema Extensions (anchors, costs, wait states, thresholds)
Layer 0: Existing Libraries (pytransitions, Pillow, imagehash, Playwright/ADB)
```

Each layer depends only on layers below it. The playbook (Layer 3) orchestrates the tools (Layer 2) which operate on the schema (Layer 1) which extends existing libraries (Layer 0).

---

## What We're Not Building

- **Agent orchestration framework** — Use Claude Code, LangGraph, or whatever. We model the external system, not the agent.
- **State machine library** — pytransitions handles this. We extend its data format.
- **Browser/mobile automation** — Playwright, ADB, Appium are action backends. We're a layer above.

---

## Open Design Decisions

These will be resolved through building, not in advance:

1. **Provider interface shape** — What's the minimal capability set? How is it configured?
2. **State consolidation heuristics** — When to split vs. merge observed states
3. **Anchor stability detection** — How to detect degrading anchors before misclassification
4. **Graph scale limits** — Where do the tools break at 100, 500, 1000+ states?
5. **Session persistence across environments** — Multi-machine, multi-agent session coherence
6. **Graph format** — JSON vs YAML vs SCXML subset for the canonical format

---

## Success Metrics

- **Cost reduction**: average transition cost drops from 50 (all vision) to <10 (mostly deterministic)
- **Orientation speed**: `locate()` returns correct state in <100ms for 90%+ of cases
- **Recovery rate**: agent recovers from "lost" state without restarting in 95%+ of cases
- **Graph construction time**: agent builds a 30-state graph in <2 hours with human guidance
- **Maintenance overhead**: <10 minutes per graph update when the external system changes
