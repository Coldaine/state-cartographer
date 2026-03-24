# State Machine Tooling for External System Automation: Conversation Synthesis

> Historical note: moved from `docs/research/RES-founding-synthesis.md` during the 2026 documentation realignment.


## The Problem

When an AI agent automates an external system (browser form, game UI, desktop app, any interface), the **external system has its own state graph**. This is distinct from the agent's orchestration state. No existing library or utility addresses the problem of:

1. **Mapping** an external system's states into a queryable, introspectable data structure
2. **Locating** the agent within that graph from observations alone (passive classification)
3. **Disambiguating** when passive classification is insufficient (active probing strategy)
4. **Replacing** expensive vision-driven transitions with cheap deterministic calls
5. **Routing** between arbitrary states via cheapest available path

Every existing state machine library (pytransitions, python-statemachine, XState) assumes the machine has been running from the start and state is tracked internally. They answer "what transitions are available from my known state?" which presupposes the hard part is solved. No library helps an agent dropped into an ongoing process figure out where it is.

This is **not** an orchestration framework problem. It has nothing to do with LangGraph, Temporal, CrewAI, or any agent framework. People using bare Claude Code with no framework hit this problem the moment something goes wrong mid-task.

## The Core Insight: State Graph as Compression Layer

Automating any external system starts maximally expensive: vision model screenshots every frame, LLM reasoning about what it sees, deciding where to click, acting, waiting, repeating. This works but is slow, expensive, and fragile.

The state graph compresses this. Once enumerated, most transitions can be replaced with deterministic function calls (ADB taps, DOM clicks, keyboard shortcuts, URL navigation, API calls). The vision/LLM path doesn't disappear; it becomes the **fallback for genuinely uncertain moments**, which is its proper role.

This is not primarily a cost optimization. Deterministic tooling is better on every axis: faster, more accurate, more reproducible. Cost savings are a side effect.

The end state: the agent calls `graph.route(current, target)` and gets a sequence of cheap deterministic transitions. The state graph is effectively an **API client for a system that never published an API**.

## The Methodology (Phases)

### Phase 1: Expensive Exploration

Point a vision agent at the system. Let it navigate. Record every screen, every action, every result. The output is raw material for graph construction, not completed tasks.

Key insight: if screenshots are captured at each state, you get a **static dataset for offline development**. The state graph, anchors, transition logic, classifiers can all be built and validated against saved images without re-driving the live system. Decouples "understanding the system" from "interacting with the system."

Exploration and graph construction are the same activity. The graph is built **while being used**; LLM navigates with whatever graph exists so far, discovers new states, adds them, graph gets richer as it goes.

### Phase 2: State Consolidation

The art of the process. Collapse observations into true states:

- **Same state, different appearance**: main menu with Monday's event banner = main menu with Tuesday's event banner. Transient content (daily events, rotating banners, timestamps) must be separated from structural identity.
- **Different state, same appearance**: "confirm sell equipment" dialog vs "confirm retire ship" dialog look identical but are different states with different consequences.
- **Identifying stable anchors**: per-state signals that persist across sessions and updates. Not "what does this screen look like" (too expensive) but "what specific, cheap-to-check signal confirms this state." DOM element presence, pixel at known coordinates, process output pattern, file existence.
- **What truly changes**: some elements change daily/weekly (event images, limited-time UI). Anchors must be chosen from the stable structural layer, not the content layer.

### Phase 3: Transition Replacement

Go state-by-state and ask: what's the cheapest reliable way to execute this transition?

Common UI patterns cover a huge percentage of the graph:
- **Back/menu buttons**: nearly universal, almost always in the same position. One wrapper covers many states.
- **Confirm/cancel dialogs**: predictable structure. The transition either goes back to the previous state or advances through the confirmation.
- Most transitions resolve to: ADB tap at coordinates, keyboard shortcut, URL navigation, DOM selector click, API call.

After replacement, remaining vision-requiring transitions should be a small minority, concentrated at genuinely dynamic or novel interaction points.

An **optimization pass by a separate LLM** reviews the completed graph to identify replacement candidates systematically. This is a distinct analytical role, not the same agent that explored.

### Phase 4: Wait State Identification

Some states don't need active management. Examples: auto-battle in a game, a long-running upload, a processing spinner. The agent detects "we're in this state," sets a timer or polling interval, and only re-engages when the state changes.

Critical because wait states are often the **longest-duration states**, and burning vision-agent tokens watching animations is pure waste. The state graph should annotate which states are wait states and what their exit conditions look like (cheap signals that indicate "something changed, wake up").

### Phase 5: Orientation Layer

Two distinct capabilities:

**5a: Passive classification ("where am I?")**
This is a **tool, not a prompt**. The agent calls `state_machine.locate()`. The tool:
- Reads currently available signals (screen content, DOM state, process output)
- Compares against annotated state graph anchors
- Uses **session history** to constrain candidates (if you were in state X three actions ago and did two known transitions, candidate set is small)
- Returns: definitive state ID, or narrowed candidate set with distinguishing criteria

Deterministic pattern matching, not LLM reasoning. The LLM is only invoked if the tool returns genuine ambiguity.

**5b: Active disambiguation ("what should I try?")**
When passive classification can't resolve, the tool suggests **probing actions**: "try pressing back and observe what happens." This narrows the candidate set. The tool can rank probes by information value (which action would most effectively distinguish between remaining candidates).

Session management is integral to the classifier, not an add-on. Without session history, every `locate()` starts from scratch. With it, most calls are trivial.

### Phase 6: Ongoing Maintenance

The external system updates (app patches, new features, UI changes). Some anchors break. The graph needs:
- Detection: "I'm seeing something I can't classify against the current graph"
- Graceful degradation: fall back to vision path for unrecognized states
- Flagging: surface unknown states for graph updates
- Confidence thresholds: for particularly sensitive transitions, the schema should support marking states where the agent should request vision/LLM review before proceeding, even if the deterministic classifier is confident

## Key Architectural Decisions

### The Graph is Per-System, Not Per-Task

The Azur Lane menu structure is the same whether you're doing daily missions, farming, or managing dock. Any desktop app's navigation layer is shared across all tasks. Only the leaf-level "do the actual thing" varies.

This means the graph is **persistent infrastructure** for a system. Build once, maintain as app updates, every task benefits.

### Pathfinding

With the full graph and traversal costs per transition (cheap function call vs requires vision), compute shortest/cheapest path between any two states. No more backtracking to home screen. If you're three screens deep in one workflow and the next task starts in an adjacent branch, the graph knows the shortcut.

### Hybrid Exploration

The ultimate workflow is an LLM navigating using the state graph itself, where:
- Known states use deterministic transitions
- Unknown/uncertain states escalate to vision
- Newly discovered states get added to the graph in real-time
- The graph improves with every session

### Human Feedback: Deferred

Human-in-the-loop for state consolidation questions and ambiguity resolution is real but should be **the last thing designed**. Thinking about it too early will cloud the architecture. Park it.

## What Does Not Exist (as of March 2026)

No library, framework, or utility provides:
- A standard format for declaring an external system's state graph with observation anchors
- A `locate()` tool that classifies current state from observations + session history
- A disambiguation planner that suggests probing actions
- A pathfinder that routes between states via cheapest transitions
- A methodology/playbook for LLMs to construct these graphs from scratch
- A multi-agent decomposition for iterative graph refinement

The closest existing primitives:
- `pytransitions/transitions` (Python, 6.4k stars, active): best introspection API (`get_triggers()`, `may_trigger()`, hierarchical states). Potential foundation.
- `python-statemachine` (Python, v3.0 Feb 2026): clean declarative API with compound/parallel states and guards.
- XState (TypeScript, 29k stars): fullest statecharts implementation. `@statelyai/agent` adds LLM-driven transition selection but still assumes known state.
- Page Object Model (Selenium/Playwright pattern): closest conceptual analogue; each page object describes "what page am I on" via expected elements and "what can I do here" via available actions. But never formalized into a queryable state machine.

## Open Questions (Unanswered)

1. How was the ALAS state machine actually discovered? Manual play, agent exploration, hybrid?
2. How deep does active disambiguation go in practice? One probing action, or multi-step? Is there a ceiling where you restart from known state?
3. When state consolidation is ambiguous, does the agent tentatively treat observations as separate states and merge later, or flag and skip?
4. What typically triggers iterative refinement of the graph? Failures during automation, or realizations during the optimization pass?
5. What form factor should initial output take? (Skill, library, methodology doc, blog post)
6. What matters most for the graph data structure? (Human-readable, runtime-queryable, visual, all three)
7. What's in scope for v1? (Format + API, classifier, disambiguation planner, transition optimizer)
