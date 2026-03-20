# NAV — Navigation

**Status: Implemented but unvalidated against live game (March 2026)**

Navigation answers: "how do I get from screen A to screen B?" Given a state graph with transitions, compute the cheapest route and execute it.

## Build order

Layer 2 — depends on Observation (must know where you are before you can navigate). Execution depends on this (tasks navigate to entry states before acting).

## What it covers

- State graph definition (graph.json — states, transitions, costs, anchors)
- Pathfinding (Dijkstra with cost weighting and deterministic preference)
- Session tracking (confirmed states, transition history)
- Graph inspection and validation

## What exists today

- `scripts/pathfind.py` — Dijkstra shortest-path with cost biasing, avoid states, prefer deterministic
- `scripts/session.py` — session state manager (confirm state, record transition, query history)
- `scripts/graph_utils.py` — graph inspection (orphans, reachability, missing anchors, Mermaid export)
- `scripts/schema_validator.py` — graph schema validation
- `scripts/alas_converter.py` — one-shot ALAS button definitions to graph transitions
- `examples/azur-lane/graph.json` — 42 states, 80+ transitions, pixel-color anchors

## What's missing

- Live validation — pathfinding works on paper but untested against the real game
- Gesture-based transitions (swipes needed for some navigation, all transitions are taps)
- Conditional transitions (transitions that only work when certain popups aren't present)
- Runtime marking of broken/unreliable transitions
- Cost learning from execution history (all costs are static `10`)
- Session history grows unbounded — no compaction

## Open questions

- Should popup/modal states be first-class graph nodes or handled as interrupts?
- How to handle the same screen with different overlays (page_main vs page_main_white)?
- Should transition costs be learned from observed latency?
- How does the graph handle game updates that add/remove/move screens?

## Key scripts

| Script | Lines | What it does |
|--------|-------|-------------|
| pathfind.py | ~130 | Dijkstra route planning with cost weighting |
| session.py | ~85 | Session state tracking (confirmed states, transition history) |
| graph_utils.py | ~180 | Graph inspection, orphan detection, Mermaid export |
| schema_validator.py | ~150 | Graph schema validation |
