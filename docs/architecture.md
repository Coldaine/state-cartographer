# Architecture

State Cartographer automates Azur Lane through four layered domains, built bottom-up. Each layer depends on the ones below it.

```
AUT  Automation     scheduling, autonomous loop, escalation
EXE  Execution      task runner, backends, actions, gestures
NAV  Navigation     state graph, pathfinding, session tracking
OBS  Observation    screenshots, VLM classification, state detection, calibration
```

Supporting domains:

```
ALS  ALAS           reference system, observation source, operational knowledge
RES  Research       technical investigations and external references
```

## Domains

| Code | Domain | Status | Doc |
|------|--------|--------|-----|
| OBS | [Observation](observation/OBS-overview.md) | Active development | Screenshots, VLM tiers, state detection, corpus, calibration |
| NAV | [Navigation](navigation/NAV-overview.md) | Implemented, unvalidated | State graph, pathfinding, session |
| EXE | [Execution](execution/EXE-overview.md) | MVP placeholder | Executor, backends, actions, gestures, resources |
| AUT | [Automation](automation/AUT-overview.md) | Scaffolded, not wired | Scheduling, runtime loop, recovery, escalation |
| ALS | [ALAS](alas/ALS-overview.md) | Running | Reference system, observation harvesting |
| RES | Research | Reference material | [VLM replay analysis](research/RES-vlm-replay-analysis.md), [Stability trap](research/RES-stability-trap-analysis.md) |

## Build order

1. **Observation** — know what's on screen (current focus, March 2026)
2. **Navigation** — get between screens cheaply
3. **Execution** — perform task actions reliably
4. **Automation** — run the full loop autonomously

## Design principles

- **Tooling does the work, agent does the thinking.** Deterministic operations are handled by the runtime. LLM reasoning is reserved for planning, anomaly detection, and judgment.
- **The graph is infrastructure, not the product.** The graph enables navigation, which enables task execution, which enables automation. Each layer adds value independently.
- **Observation-first methodology.** Build the state machine from real observations (ALAS runs → screenshots → VLM labels → calibrate), not from reading source code or guessing.
- **Existing tools are allies.** We build on ADB, vLLM, ALAS's labeled observations. We don't reimplement solved problems.

## Vision tiers

The system uses multiple vision/detection methods at different cost/capability levels. See [OBS-overview.md](observation/OBS-overview.md) for the full tier table.

## What this is not

- **Not an agent orchestration framework.** LangGraph, CrewAI, etc. manage the agent's workflow. State Cartographer automates the external system.
- **Not an ALAS fork.** ALAS is the reference implementation and observation source. State Cartographer's own harness will replace ALAS for live control.
- **Not a browser/mobile automation tool.** ADB and similar tools are action backends. The runtime logic lives above them.
