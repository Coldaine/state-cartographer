# State Machine Tooling for External System Automation

> Historical note: moved from `docs/research/RES-founding-synthesis.md` during the 2026 documentation realignment.

## Status

This is a synthesis document, not an implementation claim.

It captures the durable research thesis behind the project and separates that thesis from repo reality.

See also:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [VLM-overview.md](/mnt/d/_projects/MasterStateMachine/docs/vlm/VLM-overview.md)
- [runtime-overview.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/runtime-overview.md)

## Core Problem

When an agent automates an external system, the external system has its own state graph. That graph is not tracked by the agent automatically. The hard problems are:

1. map the external system's states into a usable data structure
2. determine current state from external observations
3. disambiguate when passive observation is not enough
4. replace expensive vision-driven transitions with cheap deterministic transitions where possible
5. route through the system using the cheapest reliable path

Off-the-shelf state-machine libraries solve internal orchestration. They do not solve external-state discovery, location, and progressive replacement of uncertain interactions.

## Durable Contribution

The durable contribution is not "another state machine library." It is the combination of:

- a state graph for an external system
- per-state observation anchors
- a deterministic `locate()` concept that uses observations plus session history
- active disambiguation when passive classification is insufficient
- transition cost awareness
- weighted routing through the graph
- a methodology for exploration, consolidation, and replacement
- offline development against saved artifacts

## Capabilities The Project Needs

These are the capabilities that matter whether or not the current repo already implements them:

### External-system state graph
- the graph models the target system, not the agent
- state must be inferred from observation, not trusted from internal memory alone

### Observation anchors
- each state needs cheap, stable confirmation signals
- anchors should be chosen from structural signals, not transient content

### Passive state classification
- `locate()` should be a tool, not a prompt
- it should combine current signals with session history
- it should return either a state or a constrained candidate set

### Active disambiguation
- when candidates remain ambiguous, the system should propose safe, informative probes
- probes should be ranked by information value, cost, and risk

### Transition cost awareness
- transitions differ materially in cost and reliability
- deterministic calls, grounding checks, and full vision reasoning should not be treated as equivalent

### Weighted routing
- pathfinding should optimize for cheapest reliable route, not just fewest hops

### Progressive replacement
- exploration can begin vision-heavy
- the graph should get cheaper over time as reliable transitions replace expensive ones

### Offline iteration
- saved screenshots, logs, and traces should support graph development without re-driving the live system every time

## Methodology

### 1. Exploration
Capture observations, actions, and outcomes while traversing the target system.

### 2. Consolidation
Decide what is a true state boundary, what is transient variation, and what stable signals identify the state.

### 3. Replacement
Replace expensive transitions with deterministic or semi-deterministic execution where confidence is high enough.

### 4. Routing
Use the graph to compute cheap paths between known regions.

### 5. Maintenance
Detect unknown states, degrade gracefully, and update the graph as the target system changes.

## Proven vs Speculative

### Proven by existing systems and prior art
- external automation needs page/state knowledge
- deterministic transitions are faster and more reliable than full vision when they can be trusted
- saved artifacts are useful for offline refinement
- ALAS is strong evidence that hand-built versions of these ideas work for one target

### Still speculative or unearned in this repo
- a trustworthy repo-owned `locate()` tool
- a trustworthy active disambiguation planner
- a trustworthy runtime that routes and recovers using this model live
- a fully codified multi-agent methodology for building and maintaining these graphs

## Practical Use

Use this document to orient on the research thesis.

Do not use it as evidence that the current repo has already earned the full stack it describes.
