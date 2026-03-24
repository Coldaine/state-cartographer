# What's Actually Novel: Capabilities Not Covered by Any Existing System

Everything below was articulated during this conversation and has no implementation, library, spec, or even well-documented pattern in any existing tooling as of March 2026. SCXML, XState, pytransitions, python-statemachine, Playwright, Selenium, Appium, LangGraph, Temporal — none of them address these.

---

## 1. The State Graph Is of the External System, Not the Agent

Every existing library models the state of the application that imports the library. The novel framing is modeling the state of **a system you don't control and are automating from the outside**. The graph describes someone else's UI, someone else's app, someone else's service. You observe it indirectly. You act on it indirectly. You don't control when it transitions; you trigger transitions and then confirm they happened.

This is a fundamentally different relationship than "I am the application and I track my own state." No existing library is designed for this use case.

## 2. Observation Anchors Per State

Each state in the graph needs annotations describing **how to confirm you're in that state using cheap, stable signals**. Not "what does this screen look like" (too expensive, requires vision), but specific lightweight checks: a DOM element's presence, a pixel color at known coordinates, a text string in process output, a file on disk.

Requirements for anchors:
- Must be **stable across sessions** (not transient content like daily event banners, timestamps, rotating promotions)
- Must be **cheap to evaluate** (the whole point is avoiding vision model invocation)
- Must be **hierarchical in cost**: check the cheapest signal first, escalate to more expensive checks only if ambiguous
- Some states will need **negative anchors**: "if I see X, I'm definitely NOT in this state" to prune candidates fast

No state machine library has a concept of "how do I know I'm in this state from external observation."

## 3. Passive State Classification: `locate()`

A deterministic tool (not an LLM prompt) that:
- Reads currently available observation signals
- Compares against the state graph's annotated anchors
- Uses **session history** to constrain candidates (if you were in state X and did transition Y, candidate set is dramatically smaller)
- Returns: definitive state ID, OR a narrowed candidate set with what distinguishes them

This is pattern matching against the anchor annotations, not reasoning. The LLM only gets involved if the deterministic classifier returns genuine ambiguity. Session history is integral, not optional: without it every `locate()` starts from scratch; with it most calls are trivial.

No existing tool does this. Dialogue State Tracking from NLP is the closest academic analogue but scoped to conversation slot-filling, not arbitrary external system states.

## 4. Active Disambiguation: "What Should I Try?"

When `locate()` returns ambiguity, the system suggests **probing actions**: "try pressing back and see what happens." "Check if element X is present." "Send this keystroke and observe the response."

Requirements:
- Rank probes by **information value** (which action most effectively distinguishes between remaining candidates)
- Consider **probe cost** (a cheap DOM check before an expensive screenshot)
- Consider **probe safety** (some probing actions might cause unwanted side effects; "don't click 'confirm purchase' to find out if you're on the checkout screen")
- This is where the LLM may legitimately get invoked: to reason about which probe strategy makes sense given the candidate set

No existing tool does this. POMDPs from decision theory formalize the math but no one has packaged it for UI automation.

## 5. Transition Cost Annotations

Each transition in the graph needs a cost profile:
- **Deterministic/cheap**: ADB tap at coordinates, DOM click, keyboard shortcut, URL navigation, API call. Milliseconds, zero tokens.
- **Vision-required/expensive**: needs screenshot + LLM interpretation. Seconds, significant token cost.
- **Fragile**: works but depends on brittle signals (pixel positions that shift, elements that load asynchronously). Needs fallback strategy.
- **Unknown**: not yet characterized. Defaults to expensive path.

No state machine spec has a concept of "this transition costs X." SCXML has `<send>` for external communications but no cost model. XState has no transition weighting.

## 6. Weighted Pathfinding Across the Graph

Given transition costs, compute the **cheapest path** between any two states. Not just shortest-hop, but cheapest considering the cost annotations. This enables:
- "I'm on screen A, I need to be on screen F": the graph returns the route that uses the most deterministic transitions
- **No more backtracking to home screen**. If you're three levels deep in one branch and need to go two levels deep in an adjacent branch, the graph knows the shortcut
- Route recalculation when a transition fails (fallback paths)

XState's `@xstate/graph` does traversal for test generation but has no concept of weighted/costed pathfinding.

## 7. State Consolidation: The Art of What's "The Same State"

This is the hardest intellectual problem in the whole methodology. When building the graph from observations, you must determine:
- **Same state, different appearance**: main menu on Monday (event banner A) vs main menu on Tuesday (event banner B). Same state. The anchor must be chosen from stable structural elements, not transient content.
- **Different state, same appearance**: "confirm sell equipment" dialog looks identical to "confirm retire ship" dialog. Different states with different consequences. The distinguishing signal is context (what action preceded this dialog), not visual appearance.
- **What changes and what doesn't**: in a live-service game like Azur Lane, events rotate constantly. You can't anchor on the promotional image. You must identify the structural skeleton that persists across content updates.
- **Iterative refinement**: you'll discover your state boundaries are wrong. Two "different" states should have been one. One "state" is actually three depending on context. The graph must support cheap restructuring.

No existing tool helps with this. It's a judgment call that requires understanding the external system's design patterns, and it's where human input is most valuable.

## 8. Wait State Identification and Annotation

Some states require no active management: auto-battle, loading screens, file uploads, processing spinners. The agent detects "we're in this state," sets a polling interval, and only re-engages when the state changes.

Requirements:
- Annotate **expected duration** (or duration range) for wait states
- Define **exit signals**: cheap checks that indicate "something changed, wake up"
- Define **timeout behavior**: what to do if the wait state persists beyond expected duration (maybe it's stuck; escalate)
- These are often the **longest-duration states**, so they're where the most vision-agent cost is wasted if not identified

No state machine library has a concept of "this state is a wait state that should be polled rather than actively managed."

## 9. The Graph as API Surface / Transition Replacement

The core economic insight: once the graph exists, each transition becomes a candidate for replacement with a cheaper implementation. The methodology for this:
- For each transition, ask: can this be a direct function call instead of vision-driven interaction?
- Common UI patterns (back button, menu button, confirm/cancel) can be wrapped once and cover a large percentage of the graph
- A **separate LLM analytical pass** reviews the completed graph specifically to identify replacement candidates. This is a distinct agent role, not the explorer.
- After replacement, the state graph IS the API. `graph.route(current, target)` returns a sequence of cheap deterministic calls.
- Vision/LLM becomes the fallback for genuinely novel or changed states, which is its proper role

This concept — progressive replacement of expensive interactions with cheap deterministic calls, governed by a state graph — has no existing implementation.

## 10. Screenshot Mock for Offline Development

If the exploration phase captures screenshots at each state, those images form a **static dataset** for developing and validating the entire system offline:
- Build and refine state graph definitions against saved images
- Develop and test observation anchors without the live system running
- Validate the `locate()` classifier against known-state screenshots
- Iterate fast and cheap; only go live when the graph is already validated

This decouples "understanding the system" from "interacting with the system." No existing tool provides this workflow.

## 11. Confidence Thresholds and Escalation

Not all states are equal in risk. The schema needs:
- **Per-state confidence requirements**: some states can tolerate "80% sure we're here, proceed." Others (purchase confirmation, irreversible actions) need explicit vision/LLM review before the agent acts, even if the deterministic classifier is confident.
- **Escalation paths**: when confidence is below threshold, route to vision model. When vision model is also uncertain, route to human. When human is unavailable, pause rather than guess.
- **"We have no clue" state**: a catch-all for when observations match nothing in the graph. Must not default to taking action; must default to safe behavior (pause, escalate, restart from known state if no other option).

## 12. The Playbook: How an LLM Should Build a State Graph

Nobody has codified the methodology for an LLM to construct a state graph of an external system. This playbook would need to cover:
- How to explore systematically (not just random navigation)
- How to record observations in a structured format during exploration
- How to identify state boundaries vs. transient changes within a state
- How to identify stable anchors vs. content that will change
- How to identify wait states and their exit conditions
- When to ask the human for input (state consolidation ambiguity, meta-knowledge about the system) vs. when to keep going
- How to validate the graph against observations
- How to iteratively refine when the graph proves wrong
- How to hand off to the optimization pass for transition replacement

This playbook is what turns a general-purpose LLM into something that can systematically build automation for any external system. It doesn't exist.

## 13. Multi-Agent Decomposition

The full graph construction and maintenance process implies distinct agent roles:
- **Explorer**: drives the vision-heavy initial navigation, records raw observations
- **Consolidator**: analyzes observations, proposes state boundaries, identifies anchors
- **Optimizer**: reviews completed graph, identifies transition replacement candidates
- **Signal Annotator**: per-state identification of cheap confirmation signals
- **Maintenance Agent**: monitors live operation, flags observations that don't match the graph, proposes updates

These run across **multiple passes**, not a single session. The graph gets richer and cheaper with each pass.

## 14. Hybrid Navigation: Using the Graph While Building It

The graph isn't built first and then used. It's built **while being used**. The LLM navigates with whatever graph exists so far:
- Known states: use deterministic transitions (cheap)
- Unknown states: fall back to vision (expensive)
- Newly discovered states: add to graph in real-time
- Graph improves with every session

This means the cost curve decreases over time even without explicit optimization passes. Early sessions are expensive; later sessions are cheap because most of the graph is filled in.

---

## Summary: The Actual Novel Contribution

The novel thing is **not** another state machine library. The data structure and execution semantics are solved (SCXML/Harel, 1987-2015). The novel thing is the **complete system for using a state machine as an evolving model of an external system you're automating**, including:

1. A schema extending existing state machine formats with observation anchors, transition costs, wait state annotations, and confidence thresholds
2. A deterministic `locate()` tool with session-aware state classification
3. An active disambiguation planner
4. Weighted pathfinding for cheapest-route navigation
5. A methodology/playbook for LLM-driven graph construction from exploration
6. A progressive replacement workflow for collapsing expensive interactions into cheap calls
7. Offline development via screenshot mocks
8. Multi-agent decomposition across construction and maintenance phases

Items 1-4 are tooling. Items 5-8 are methodology. Both are needed. Neither exists.
