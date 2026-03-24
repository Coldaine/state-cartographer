# State Cartographer — Development Instructions

## What this project is

This repo contains State Cartographer, a supervised automation runtime for
external systems. It includes graph/schema definitions, navigation tooling,
task execution tooling, supervision playbooks, and Claude-facing integration
files. The product goal is not "agent clicks through screenshots forever"; it
is "runtime plays the loop, agent supervises the runtime."

The intended control surface for an agent session is:

1. **High-level runtime calls** such as `execute_task("commission")`,
   `navigate_to("page_dorm")`, and `ensure_game_ready()`
2. **Supervisory queries** such as `where_am_i()`,
   `why_did_last_transition_fail()`, and `show_recent_failures()`
3. **Escalation payloads** pushed up by the runtime with screenshot, current
   candidates, recent actions, and proposed recovery paths

The runtime/backend should own screenshot capture, low-level emulator I/O,
state verification, and event logging. Direct screenshot tooling remains useful
for debugging, calibration, and exploration, but it is not the normal operator
interface.

## Current Phase: Observation-to-State-Machine Build

**We are in the phase between corpus collection and deterministic navigation.**

The pipeline is:

```
ALAS runs live (screenshot.py patched directly in vendor/)
    ↓ saves every frame to data/raw_stream/<YYYYMMDD_HHMMSS_mmm>.png
    ↓ ALAS logs page labels with millisecond timestamps (log/YYYY-MM-DD_PatrickCustom.txt)
label_raw_stream.py joins log timestamps → data/raw_stream/index.jsonl
    ↓ frames with matching log entries get alas_page label
    ↓ remaining unlabeled frames → VLM (vlm_detector.py / Qwen3.5-9B-AWQ)
State machine authors & validates graph.json
    ↓ Every page in ALAS represented, transitions verified
    ↓ calibrate.py uses VLM-labeled corpus to sample real RGB anchors
locate.py works on real screenshots (production path)
    ↓ deterministic, fast, no VLM needed
Executor + Scheduler drive live game
```

**What works now:** ALAS monkeypatch capture ✓ | DroidCast screenshots ✓ |
VLM detection ✓ | Event log pipeline ✓ | pilot_bridge.py tap/swipe ✓

**What's next:** Full state machine graph authored from corpus | calibrate.py
recalibrated from real ALAS screenshots | locate.py validated on live frames |
pilot-driven navigation loops

### On locate.py and calibrate.py

These are **not obsolete** — they are the production destination. VLM is the
bootstrap bridge.

- `locate.py` — the cheap, deterministic, always-on state classifier. Currently
  returns "unknown" for all real frames because the RGB anchors in `graph.json`
  came from ALAS source code tuples, not sampled from real pixels. Once
  calibrated, it replaces VLM entirely for classification.
- `calibrate.py` — the tool that samples real pixel values from VLM-labeled
  screenshots and writes calibrated anchors back into `graph.json`. This is
  the step that will fix locate.py.
- `vlm_detector.py` — current state detector (Qwen3.5-9B-AWQ @ localhost:18900).
  Used for corpus labeling AND as the runtime fallback until locate.py is
  calibrated. Will become the LLM escalation path once locate.py works.

## Current canonical live entrypoint

For live MEmu/Azur Lane control, the single supported entrypoint today is:

- `scripts/executor.py`
- `execute_task_by_id(...)`
- backend `pilot`

Use `python scripts/executor.py --backend pilot --serial 127.0.0.1:21513 ...` for live execution, and `--preflight-only` when you need an explicit readiness proof. Do not treat raw `adb_bridge.py` or direct vendor ALAS launch as interchangeable control-plane entrypoints.

`scripts/pilot_bridge.py` **is** the pilot backend — it owns DroidCast screenshot
capture, ADB tap/swipe, and NDJSON event recording. It is imported by
`executor.py`; use the executor as the entry point rather than instantiating
`PilotBridge` directly unless you are debugging the screenshot/action layer.
See `docs/execution/EXE-pilot-bridge-rework.md` for the planned cleanup.

**ALAS is reference architecture and the active labeled-corpus source.** The
project's design is validated against AzurLaneAutoScript (ALAS). Running ALAS
normally generates screenshot corpus — `vendor/AzurLaneAutoScript/module/device/screenshot.py`
is patched directly to save every frame to `data/raw_stream/`. ALAS logs provide
page labels; `label_raw_stream.py` joins them to the timestamped PNGs. The live
control path for State Cartographer's own automation is `executor.py` + `pilot_bridge.py`.

## ALAS observation pipeline (active — not optional)

See `docs/alas/ALS-live-ops.md` for hard rules and `docs/observation/OBS-overview.md` for the
full capture/labeling pipeline. Short version: screenshot capture is patched directly into
`vendor/AzurLaneAutoScript/module/device/screenshot.py` — run ALAS normally, frames land in
`data/raw_stream/`. After a run, join ALAS log timestamps to label the corpus:

```bash
uv run python scripts/label_raw_stream.py \
  --log vendor/AzurLaneAutoScript/log/$(date +%Y-%m-%d)_PatrickCustom.txt \
  --raw-stream data/raw_stream
```

### Clean slate before every ALAS launch (MANDATORY)

```powershell
# 1. Kill all ALAS/Python processes
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'gui\.py|AzurLane' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 2. Free port 22267
Get-NetTCPConnection -LocalPort 22267 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 3
```

### Launch command

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
cd D:\_projects\MasterStateMachine\vendor\AzurLaneAutoScript
.\.venv\Scripts\python.exe gui.py --run PatrickCustom
```

### Venv setup (only needed once, or after wiping venv)

The venv MUST be Python 3.9, built from the frozen requirements:

```powershell
uv venv .venv --python 3.9 --clear
# Strip the header line from the frozen file first, then:
uv pip install --python .venv\Scripts\python.exe `
  -r ..\alas_requirements_clean.txt --no-deps
```

`vendor/alas_requirements_clean.txt` is the pip-frozen environment from the
working `alas_wrapped` venv (all 88 packages at exact versions). Do NOT try to
install from scratch or resolve dependencies — use `--no-deps` always.

These `vendor/alas*_*.txt` snapshots and helper launch scripts are local setup
artifacts and should remain untracked.

### Config setup (fresh clone only)

**Never copy PatrickCustom.json from alas_wrapped** — the schema changes between
versions. Instead:
1. Start from `config/template.json` (upstream schema)
2. Set emulator: `Serial=127.0.0.1:21513`, `PackageName=com.YoStarEN.AzurLane`,
   `ScreenshotMethod=uiautomator2`, `ControlMethod=MaaTouch`
3. Enable tasks: Restart, Commission, Research, Dorm, Meowfficer, Guild, Reward,
   Awaken, Daily, Hard, Exercise, ShopFrequent, ShopOnce, Shipyard, Freebies,
   PrivateQuarters, OpsiAshBeacon, OpsiAshAssist, OpsiDaily, OpsiObscure,
   OpsiAbyssal, OpsiArchive, OpsiStronghold, OpsiMonthBoss, OpsiMeowfficerFarming
4. Set all NextRun to `"2020-01-01 00:00:00"` so tasks run immediately

### What normal looks like

- Black frames during login = normal Unity loading, not an error
- `Restart` task firing = ALAS's built-in error recovery, not a crash
- Multiple python.exe processes = normal (main + worker processes)
- Log at: `vendor/AzurLaneAutoScript/log/2026-MM-DD_PatrickCustom.txt`

## Project structure

- `skills/`    — Skill playbooks (SKILL.md files).
- `agents/`    — Subagent definitions (explorer, consolidator, optimizer).
- `commands/`  — Slash commands.
- `rules/`     — Always-on rules (safety, orientation, graph-maintenance).
- `scripts/`   — Python tooling (locate, pathfind, session, etc.).
- `hooks/`     — Claude Code hooks (hooks.json, post_write.py).
- `docs/`      — Design docs and architecture decisions. Read these first.
- `tests/`     — pytest tests for scripts/.
- `examples/`  — Example graph definitions for reference and testing.

## When working on this project

- Read `docs/NORTH_STAR.md` for the vision and guiding principles.
- Read `docs/research/RES-founding-synthesis.md` and `docs/research/RES-novel-capabilities.md` for full context.
- Read `docs/architecture.md` for the layer mapping and design decisions.
- Read `docs/plans/plan.md` for the current execution plan and script status table.
- The Python scripts in `scripts/` are the hard tooling. They must have
  tests. Run: `uv run pytest tests/ -v`
- The markdown files in `skills/`, `agents/`, `commands/`,
  `rules/` are the methodology. They must be clear, opinionated, and
  follow progressive disclosure (SKILL.md under 500 lines, deeper content
  in references/).
- Do not confuse "dev agents" (us, working on the runtime) with "plugin agents"
  (explorer.md, consolidator.md, optimizer.md — these are the product).

## Two kinds of agents

1. **Dev agents** (defined in root `AGENTS.md`): agents that work on building/improving the plugin.
2. **Plugin agents** (defined in `agents/`): agents that end users invoke when using the plugin.

When editing `agents/explorer.md`, you are writing instructions for a *future agent
that will explore external systems*. You are not that agent.

## Coding conventions

- Python: type hints, docstrings, no classes where functions suffice
- Dependencies: `pyproject.toml` (managed with UV)
- Graph definitions: JSON with extended schema (anchors, costs, wait states, thresholds)
- See `docs/architecture.md` Layer 1 for schema details.

## Testing

```bash
uv run pytest tests/ -v
uv run pytest tests/ --cov=scripts --cov-report=html
```

## Linting

```bash
uv run ruff check scripts/ tests/ hooks/ --fix
uv run ruff format scripts/ tests/ hooks/
```

## Key files to read first

1. `docs/NORTH_STAR.md` — the vision
2. `docs/research/RES-founding-synthesis.md` — the full problem statement
3. `docs/research/RES-novel-capabilities.md` — what's novel vs what exists
4. `docs/architecture.md` — layer mapping, capability assignments
5. `docs/plans/plan.md` — current script status, pivot decisions, phase exit criteria
