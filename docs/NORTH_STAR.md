# North Star

## The Problem

When an AI agent automates an external system, whether a web app, a mobile game, a desktop application, or any interactive interface, it has no model of that system. It sees pixels. It reasons about what those pixels mean. It decides where to click. It clicks. It waits. It screenshots again. It reasons again.

This works. It's also absurdly expensive, slow, fragile, and unnecessary for the vast majority of interactions. The agent is spending its most powerful capability (general intelligence) on tasks that don't require it (clicking a known button in a known location to reach a known screen).

The deeper problem surfaces when something goes wrong. The page changes unexpectedly. The automation crashes mid-task. A new session starts and the agent has no idea where the previous one left off. The universal recovery strategy today is: go back to the beginning and start over. There is no way for the agent to look around, figure out where it is, and pick up where it left off.

## The Insight

Every external system has a state graph. Screens, pages, menus, dialogs, modes: these are states. Buttons, links, gestures, commands: these are transitions. This graph exists whether or not anyone has written it down.

If you write it down, three things become possible:

1. **Cheap navigation.** Most transitions can be executed as deterministic function calls (a tap at known coordinates, a URL, a keyboard shortcut) instead of vision-driven reasoning. The state graph becomes an API for a system that never published one.

2. **Self-orientation.** Given observable signals and a state graph, the agent can determine where it is without starting over. The graph annotates each state with cheap confirmation signals; the agent checks them instead of reasoning from raw pixels.

3. **Progressive optimization.** The graph starts expensive (vision-driven everywhere) and gets cheaper over time as transitions are replaced with deterministic calls and states are annotated with lightweight confirmation signals. Every session teaches the system something.

## The Vision

State Cartographer is a toolkit and methodology for building, maintaining, and navigating queryable state graphs of external systems. It enables an AI agent to:

- **Map** an unfamiliar system into a structured, introspectable state graph through guided exploration
- **Orient** itself within that graph from observable signals, even after crashes, interruptions, or cold starts
- **Navigate** between any two states via the cheapest available path, using deterministic transitions wherever possible and falling back to vision only when necessary
- **Improve** the graph over time: discovering new states, refining boundaries, replacing expensive transitions with cheap ones, and detecting when the external system has changed

The end state is that automating an external system follows the same arc as building any other integration: expensive and manual at first, then progressively cheaper and more reliable as the model matures.

## Goals

### 1. An agent should be able to answer "where am I?" cheaply

Given a state graph with annotated observation signals, the agent calls a deterministic tool that checks those signals against the graph and returns the current state. No LLM reasoning required for the common case. LLM reasoning is reserved for genuine ambiguity.

### 2. An agent should be able to answer "how do I get there?" cheaply

Given a current state and a target state, the agent gets back a route composed of the cheapest available transitions. Most routes consist entirely of deterministic function calls. The agent executes them without needing to see or reason about intermediate screens.

### 3. An agent should be able to recover from "I'm lost" without starting over

When the agent can't determine its state, it should have a structured strategy for disambiguation: specific probing actions ranked by information value and cost. Restarting from a known state is the last resort, not the first.

### 4. The graph should be buildable by an agent, not just by a human

An LLM agent, guided by a methodology, should be able to explore an unfamiliar system and construct the initial state graph. The human provides domain knowledge and judgment calls at specific decision points; the agent does the systematic navigation and observation work.

### 5. Existing environment connections should be reused, not reinvented

When the user already has tooling for interacting with the target system (an ADB connection, a Playwright session, an existing automation framework), the cartographer should adapt to that tooling rather than building its own. The skill defines what capabilities it needs; the user provides how those capabilities are fulfilled.

### 6. The graph should get better with use

Every automation session is an opportunity to validate existing states, discover new ones, and test transition reliability. The graph is a living document that improves passively through use and actively through dedicated optimization passes.

### 7. The methodology should be teachable to an LLM

The full process, from initial exploration through consolidation, optimization, and maintenance, should be captured as a playbook that an LLM can follow. Not just "here are the tools" but "here is how to think about state boundaries, here is how to choose stable anchors, here is when to ask the human."

## What This Is Not

- **Not another agent orchestration framework.** This does not compete with LangGraph, CrewAI, or any tool that manages the agent's own workflow. This models the external system the agent is automating.
- **Not another state machine library.** The state machine data structures and semantics are solved problems (SCXML, Harel statecharts, 1987). We use existing libraries for that. The novel work is everything built on top: observation anchors, self-orientation, weighted pathfinding, and the construction methodology.
- **Not a browser automation tool.** Playwright, Selenium, ADB, and Appium are action execution backends. They're one possible implementation of transitions. The graph works regardless of what system is being automated or how.

## Open Questions We Know We Need to Answer

These are real problems we've identified but haven't solved yet. They are documented here so that the solutions are discovered through building, not assumed in advance.

**State consolidation heuristics.** When does an agent decide two observations are the same state versus different states? What signals indicate "this is transient content on a persistent screen" versus "this is a genuinely different screen"? The methodology says to ask the human at ambiguous decision points, but the heuristics for what counts as ambiguous need to be discovered through practice.

**Anchor stability detection.** How does the system detect that an anchor has become unreliable before it causes a misclassification? An app update might move a UI element, change text, or restructure a screen. The graph needs to degrade gracefully rather than silently giving wrong answers.

**Provider interface design.** The adapter layer between the cartographer's tools and the user's existing automation environment needs to be simple enough to set up quickly and flexible enough to cover diverse systems (web, mobile, desktop, game, CLI). The right abstraction boundary hasn't been found yet.

**Active disambiguation strategy.** When `locate()` returns ambiguity, the system should suggest probing actions. Ranking those probes by information value and safety is a decision-theoretic problem. How much formalism is needed versus simple heuristics?

**Graph schema format.** The extended schema (observation anchors, transition costs, wait states, confidence thresholds) needs to be specified precisely enough for tooling to operate on it, while remaining readable enough for humans and LLMs to author and edit directly. The right balance between structured data and natural language annotations is an open design question.

**Session persistence across environments.** When automation involves multiple tools, multiple machines, or multiple agent sessions, how does session history stay coherent? The session manager tracks state within a single run, but real automation workflows often span sessions.

**Scale of the state graph.** The examples we've discussed (game menus, web forms) have tens to low hundreds of states. Do the tools and methodology hold up for systems with thousands of states? Where are the performance and usability cliffs?

**When to stop exploring.** During the exploration phase, how does the agent know it has sufficient coverage? Some states may be rare, gated behind conditions, or only reachable through specific sequences. What counts as "good enough" for a first version of the graph?

## Guiding Principles

**Deterministic by default, intelligent by exception.** The common path should involve no LLM reasoning. Vision and reasoning are the expensive fallback for genuinely uncertain situations.

**The graph is infrastructure, not a one-time artifact.** Like an API client or a test suite, the graph is maintained alongside the system it models. It has a lifecycle that extends beyond initial construction.

**Existing tools are allies.** We build on top of SCXML semantics, pytransitions, Playwright, ADB, and whatever else the user already has. We don't reimplement solved problems.

**The human stays in the loop for judgment, not for labor.** The agent does the systematic work. The human provides the domain knowledge and makes the calls that require understanding intent, consequence, or business context.

## Reference Case

ALAS (AzurLaneAutoScript) is the existence proof. Over 9 years, it built a 43-state page graph for Azur Lane with color-based anchors, BFS pathfinding, deterministic transitions, and recovery from unknown states. Every problem State Cartographer addresses — state detection, cheap navigation, orientation, progressive optimization — ALAS solved by hand for one specific system.

State Cartographer exists because that manual process should be a playbook, not a heroic engineering effort. The ALAS page graph (`module/ui/page.py`, `module/ui/assets.py`, `module/ui/ui.py`) is the canonical reference for validating our schema, tools, and methodology against a real, battle-tested system.
