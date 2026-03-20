# AUT — Automation

**Status: Scaffolded but not wired (March 2026)**

Automation answers: "what runs when, and what happens when things go wrong?" The autonomous loop that picks tasks, executes them, handles errors, and escalates genuine decisions.

## Build order

Layer 4 — the top layer. Depends on Execution (runs tasks), Navigation (routes to entry states), and Observation (detects state). This is the last thing to build and the thing that makes the system autonomous.

## What it covers

- Task scheduling (priority queue, time-based, resource-gated)
- The autonomous runtime loop (pick task → execute → reschedule → sleep → repeat)
- Error recovery and retry logic
- Escalation with rich context (screenshot, candidates, recent actions, proposals)
- Decision support (structured escalation for judgment calls)
- Supervision interface (what the supervisor sees and can control)

## What exists today

- `scripts/scheduler.py` — priority-based task picker, next-run computation, resource gating (MVP placeholder)
- The scheduler and executor exist independently but are **never connected**

## What's missing

- **The runtime loop** — there is no daemon. No `while True: pick → execute → reschedule`. This is the single biggest gap between "toolkit" and "automation."
- **Error recovery catalog** — `error_strategy` fields exist in tasks.json but are completely ignored by the executor
- **Escalation mechanism** — no way to push context up to a supervisor when stuck
- **Decision support** — no structured escalation for complex decisions
- **Supervision interface** — no MCP tools, no function-calling wrappers, no query interface
- **next_run is never updated** — after a task completes, nothing calls compute_next_run() or writes back

## Open questions

- What does the runtime loop look like? Python `while True` or a separate orchestrator?
- How does escalation work? Webhook? File on disk? MCP call to Claude?
- When a task fails, what determines retry vs skip vs escalate?
- How does the supervisor interact? CLI? MCP tools? Direct API?

## Key scripts

| Script | Lines | What it does |
|--------|-------|-------------|
| scheduler.py | ~200 | Priority-based task picker, next-run computation |
