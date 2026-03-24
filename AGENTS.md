# AGENTS.md — Documentation Index

> This file is the mandatory starting point. Read this before anything else.

> **Current Phase (2026-03-20):** Observation-to-State-Machine Build — ALAS corpus
> collected, labeling in progress, state machine being authored, pilot_bridge.py
> rework planned. See `CLAUDE.md` for the full phase description.

## Required Reading (Start Here)

| Document | What It Covers |
|----------|--------------|
| [MASTER_PLAN.md](MASTER_PLAN.md) | Master plan: development phases, key workflows, success metrics |
| [CLAUDE.md](CLAUDE.md) | Project conventions, commands, coding standards — **read this for current phase** |
| [docs/NORTH_STAR.md](docs/NORTH_STAR.md) | Vision, goals, guiding principles, open questions |
| [docs/architecture.md](docs/architecture.md) | 4-domain architecture (OBS/NAV/EXE/AUT), layer mapping |
| [docs/execution/EXE-workflows.md](docs/execution/EXE-workflows.md) | Azur Lane workflow inventory |
| [docs/execution/EXE-data-collection.md](docs/execution/EXE-data-collection.md) | Data collection design (planned) |
| [docs/plans/plan.md](docs/plans/plan.md) | **Current execution plan — script status, pivot decisions, phase exit criteria** |

## Current Project Direction

State Cartographer is a supervised automation runtime. The path forward is:

- The runtime/backend owns screenshot capture, low-level emulator I/O, state verification, and event recording
- The executor and daemon use those capabilities internally for `locate`, navigation verification, recovery, and logging
- The agent operates through a higher-level control surface, not by manually requesting screenshots before every action

The intended agent-facing interface has three levels:

1. **High-level runtime calls** such as `execute_task("commission")`, `navigate_to("page_dorm")`, and `ensure_game_ready()`
2. **Supervisory queries** such as `where_am_i()`, `why_did_last_transition_fail()`, and `show_recent_failures()`
3. **Escalation payloads** pushed up by the runtime with screenshot, current candidates, recent actions, and proposed recovery paths

## Current Canonical Live Entrypoint

Until a daemon/runtime API ships, treat this as the single supported live entrypoint for MEmu/Azur Lane:

- `scripts/executor.py`
- backend: `pilot`
- callable surface: `execute_task_by_id(...)`
- CLI surface: `python scripts/executor.py --backend pilot --serial 127.0.0.1:21513 ...`

Required live preflight is owned by this entrypoint. Do **not** treat `scripts/pilot_bridge.py`, `scripts/adb_bridge.py`, vendor ALAS launchers, or ad-hoc `observe.py` / `locate.py` invocations as equivalent top-level ways into the system. Those are debug or observation tools.

## Reference Case: ALAS (AzurLaneAutoScript)

ALAS is the existence proof for State Cartographer. It is a 9-year-old Python automation framework for Azur Lane that has already solved — by hand — every problem this project generalizes:

- 43 page definitions with color-based state detection anchors
- BFS pathfinding between pages
- Deterministic navigation via button clicks at known coordinates
- Recovery from unknown states via GOTO_MAIN fallback
- Per-locale support (cn/en/jp/tw)

**ALAS is reference architecture and optional corpus source material, not the runtime we are shipping.** Its page graph, button definitions, and navigation logic validate whether our schema, tools, and playbook are complete enough to represent a real-world system. We may mine ALAS for examples or labeled observations, but the live control path moving forward is State Cartographer's own executor/backend stack. Any agent working on this project should understand that ALAS's `module/ui/page.py` (state graph), `module/ui/assets.py` (anchor definitions), and `module/ui/ui.py` (locate + navigate) are canonical examples of the pattern we are reproducing.

| ALAS Component | State Cartographer Equivalent |
|---|---|
| `Page` class + `page.py` | `graph.json` state definitions |
| `Button.color` + `Button.area` | `pixel_color` anchors with `expected_rgb` |
| `Button.button` (click region) | Transition `action` with `adb_tap` coordinates |
| `Page.links` | `transitions` in graph.json |
| `UI.ui_get_current_page()` | `scripts/locate.py` |
| `UI.ui_goto(destination)` | `scripts/pathfind.py` |
| `Page.init_connection()` (BFS) | Dijkstra's in `pathfind.py` |
| GOTO_MAIN fallback | Recovery strategy in `rules/orientation.md` |

The ALAS repo is available as a git submodule at `vendor/AzurLaneAutoScript/`.

## Design Documents

| Document | Topic |
|----------|-------|
| [docs/plans/plan.md](docs/plans/plan.md) | **Current execution plan** — replaces all older plan docs |
| [docs/execution/EXE-workflows.md](docs/execution/EXE-workflows.md) | All Azur Lane workflows with entry states, OCR regions, decisions |
| [docs/execution/EXE-data-collection.md](docs/execution/EXE-data-collection.md) | Ship census, stat recording, pagination engine (planned) |
| [docs/alas/ALS-event-schema.md](docs/alas/ALS-event-schema.md) | NDJSON event log schema for recording all actions |
| [docs/research/RES-alas-build-plan.md](docs/research/RES-alas-build-plan.md) | Concrete work program for ALAS → SC artifact conversion |
| [docs/alas/ALS-live-ops.md](docs/alas/ALS-live-ops.md) | Hard rules for live ALAS harness operation |
| [docs/research/RES-founding-synthesis.md](docs/research/RES-founding-synthesis.md) | State machine tooling synthesis — survey of existing tools |
| [docs/research/RES-novel-capabilities.md](docs/research/RES-novel-capabilities.md) | Capabilities no existing library provides |
| [docs/research/RES-vlm-live-observer.md](docs/research/RES-vlm-live-observer.md) | VLM as continuous live observer — state stream, session memory, rich escalation |
| [docs/testing-strategy.md](docs/testing-strategy.md) | Testing approach (TODO: needs rewrite) |
| [docs/decisions/001-python-over-typescript.md](docs/decisions/001-python-over-typescript.md) | ADR: Why Python instead of TypeScript |

## Plugin Structure

### Skills (Playbooks)

| Skill | Purpose |
|-------|---------|
| [skills/state-graph-authoring/SKILL.md](skills/state-graph-authoring/SKILL.md) | Core playbook: exploration → consolidation → optimization → maintenance |

### Agents (Subagent Definitions)

| Agent | Role |
|-------|------|
| [agents/explorer.md](agents/explorer.md) | Vision-heavy BFS navigation, builds raw observation dataset |
| [agents/consolidator.md](agents/consolidator.md) | Analyzes observations, chooses anchors, produces graph.json |
| [agents/optimizer.md](agents/optimizer.md) | Replaces vision transitions with deterministic alternatives |

### Rules (Always-On)

| Rule | Governs |
|------|---------|

| [rules/graph-maintenance.md](rules/graph-maintenance.md) | When and how to update the graph during operation |

### Scripts (Runtime Tools)

#### Layer 2: Navigation
| Script | Function |
|--------|----------|
| `scripts/locate.py` | Passive state classifier — "where am I?" |
| `scripts/pathfind.py` | Weighted route planner — "how do I get there?" |
| `scripts/session.py` | Session state manager — tracks confirmed states and transitions |
| `scripts/graph_utils.py` | Graph inspection utilities — list states, find orphans, check reachability |
| `scripts/schema_validator.py` | Schema validator — checks graph.json integrity |
| `scripts/screenshot_mock.py` | Mock/screenshot manager — capture and validate against graph |
| `scripts/observe.py` | Observation extractor — builds obs dict from screenshot or live ADB capture |
| `scripts/calibrate.py` | Anchor calibrator — learns pixel colors / hashes from real screenshots |
| `scripts/adb_bridge.py` | ADB bridge — screenshot, tap, swipe, keyevent for MEMU/Android emulators |

#### Layer 3-4: Task Engine + Scheduler
| Script | Function |
|--------|----------|
| `scripts/task_model.py` | Task manifest load/validate/save — schedule types, action types |
| `scripts/resource_model.py` | Resource store — threshold gating, timer tracking, persistence |
| `scripts/scheduler.py` | Priority-based task scheduling with resource constraints |
| `scripts/executor.py` | Task execution engine — auto navigation + auto session tracking |

#### Recording + Instrumentation
| Script | Function |
|--------|----------|
| `scripts/execution_event_log.py` | Append-only NDJSON event stream — records every action |
| `scripts/alas_event_instrumentation.py` | Monkeypatch instrumentation for ALAS method recording |
| `scripts/alas_log_parser.py` | Structures ALAS text logs into task runs + error analysis |

#### ALAS Reference Tools
| Script | Function |
|--------|----------|
| `scripts/alas_converter.py` | Generates graph.json from ALAS page definitions |
| `scripts/alas_command_inventory.py` | Enumerates all ALAS scheduler commands/tasks |
| `scripts/alas_action_inventory.py` | Enumerates all ALAS emulator actions |
| `scripts/alas_corpus_summarize.py` | Summarizes observation corpus from ALAS runs |
### References

| Reference | Content |
|-----------|---------|
| [skills/state-graph-authoring/references/schema.md](skills/state-graph-authoring/references/schema.md) | Complete graph.json schema specification |

## Examples

| Example | Description |
|---------|-------------|
| [examples/azur-lane/](examples/azur-lane/) | In-progress Azur Lane reference graph derived from ALAS concepts |
| [examples/simple-web-form/](examples/simple-web-form/) | Small realistic example for navigation and authoring flows |
| [examples/template/](examples/template/) | Starter 3-state graph template with README |

## Project Meta

| File | Purpose |
|------|---------|
| [README.md](README.md) | Project overview for GitHub |
| [LICENSE](LICENSE) | MIT License |
| [.githooks/pre-commit](.githooks/pre-commit) | Local staged-file formatter for Python edits |
| [docs/bootstrap.md](docs/bootstrap.md) | Original bootstrap instructions (historical reference) |
