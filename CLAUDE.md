# State Cartographer — Development Instructions

## What this project is

This repo contains a Claude Code plugin called state-cartographer. The plugin
helps agents build queryable state graphs of external systems they're automating.
The plugin content (skills, agents, rules, scripts, commands) lives at root level.
Dev infrastructure lives in `docs/`, `tests/`, `examples/`, and `dev/`.

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
- `dev/`       — Dev utilities.

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
