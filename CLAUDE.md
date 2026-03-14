# State Cartographer — Development Instructions

## What this project is

This repo contains a Claude Code plugin called state-cartographer. The plugin
helps agents build queryable state graphs of external systems they're automating.
The plugin content (skills, agents, rules, scripts, commands) lives at root level.
Dev infrastructure lives in `docs/`, `tests/`, and `examples/`.

**ALAS is the live harness.** The project's design, schema, and playbook are
validated against AzurLaneAutoScript (ALAS), a 9-year-old automation framework
that solved these problems by hand for Azur Lane. ALAS runs live as a harness
for Phase 1 observation gathering — we siphon labeled screenshots from it to
build the state graph dataset. State Cartographer generalizes the approach into
a playbook any LLM agent can follow for any external system.

## ALAS harness — how to run it (READ THIS EVERY SESSION)

The ALAS harness lives at `vendor/AzurLaneAutoScript`. It is the
**Zuosizhu/Alas-with-Dashboard** fork (updated weekly), NOT LmeSzinc/upstream.

### Clean slate before every launch (MANDATORY)

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
1. Start from `config/template.json` (Zuosizhu's current schema)
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
- Read `docs/synthesis.md` and `docs/novel-capabilities.md` for full context on
  what this plugin does and why.
- Read `docs/architecture.md` for the layer mapping and design decisions.
- Read `docs/revisions-and-open-design-spaces.md` for corrected premature decisions.
- The Python scripts in `scripts/` are the hard tooling. They must have
  tests. Run: `uv run pytest tests/ -v`
- The markdown files in `skills/`, `agents/`, `commands/`,
  `rules/` are the methodology. They must be clear, opinionated, and
  follow progressive disclosure (SKILL.md under 500 lines, deeper content
  in references/).
- Do not confuse "dev agents" (us, working on the plugin) with "plugin agents"
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
2. `docs/synthesis.md` — the full problem statement
3. `docs/novel-capabilities.md` — what's novel vs what exists
4. `docs/architecture.md` — layer mapping, capability assignments
5. `docs/revisions-and-open-design-spaces.md` — corrected assumptions
