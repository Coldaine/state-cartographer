# State Cartographer

An automation runtime for external systems. State Cartographer combines state graphs, deterministic navigation, task scheduling, live executor backends, and supervision playbooks so the tooling runs the loop and the agent supervises it.

## What This Is

When an AI agent automates an external system (web app, mobile game, desktop application), it has no model of that system. It sees pixels, reasons about them, clicks, waits, and repeats. This works but is slow, expensive, and fragile.

State Cartographer provides:

- **A schema** extending standard state machine formats with observation anchors, transition costs, wait state annotations, and confidence thresholds
- **Runtime navigation tools** (`locate`, `pathfind`, `session`, `observe`) for deterministic state classification and route planning
- **Task runtime components** (`executor`, `scheduler`, `resource_model`, `execution_event_log`) for autonomous task execution and recording
- **A methodology/playbook** for LLM-driven graph construction, validation, and maintenance

The state graph becomes an API for a system that never published one.

## Agent Control Surface

In the target architecture, the agent does not micromanage screenshots or raw taps during normal operation. The runtime owns screenshot capture, low-level emulator I/O, state verification, and event recording.

The agent should usually interact at one of these levels:

1. **High-level runtime calls** such as `execute_task("commission")`, `navigate_to("page_dorm")`, and `ensure_game_ready()`
2. **Supervisory queries** such as `where_am_i()`, `why_did_last_transition_fail()`, and `show_recent_failures()`
3. **Escalation payloads** pushed up by the runtime with screenshot, current candidates, recent actions, and proposed recovery paths

Explicit screenshot tooling still matters for debugging, calibration, and exploration, but it is not the steady-state operator interface.

## Why This Exists

This project was inspired by [ALAS (AzurLaneAutoScript)](https://github.com/Zuosizhu/Alas-with-Dashboard), a 9-year-old automation framework that built a complete 43-state page graph for the mobile game Azur Lane — by hand, over years of iteration. ALAS proved the pattern: color-based state detection, BFS pathfinding, deterministic navigation, and recovery from unknown states.

State Cartographer generalizes that approach into a **runtime and methodology** that an LLM agent can supervise for *any* external system. The playbook replaces years of manual iteration with systematic graph construction and task runtime design.

ALAS's page definitions, button coordinates, and navigation logic serve as the primary reference case for validating that our schema and tools are expressive enough to represent real-world systems. ALAS is reference architecture and corpus source material, not the runtime control plane of this project.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/Coldaine/state-cartographer.git
cd state-cartographer

# Install with UV (creates .venv automatically)
uv sync --extra dev          # test tooling (pytest, ruff)
uv sync --extra vision       # screenshot/vision support (Pillow, imagehash)
# Or install everything:
uv sync --extra dev,vision

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check scripts/ tests/ hooks/ --fix
uv run ruff format scripts/ tests/ hooks/
```

## Project Structure

```
state-cartographer/
├── .claude-plugin/        # Claude Code plugin manifest
│   └── plugin.json
├── skills/                # Skill playbooks (SKILL.md files)
├── agents/                # Subagent definitions
├── commands/              # Slash commands
├── rules/                 # Always-on rules
├── scripts/               # Python tooling
├── hooks/                 # Claude Code hooks
│   ├── hooks.json
│   └── post_write.py
├── docs/                  # Design documents and architecture decisions
│   ├── NORTH_STAR.md      # Vision and guiding principles
│   ├── synthesis.md       # Full problem statement and conversation synthesis
│   ├── novel-capabilities.md  # What's novel vs what exists
│   ├── architecture.md    # Layer mapping and architectural decisions
│   └── decisions/         # Architecture Decision Records
│
├── tests/                 # pytest tests for scripts
├── examples/              # Example graph definitions
├── pyproject.toml         # Project config and dependencies
└── dev/                   # Development utilities
```

## Documentation

See [MASTER_PLAN.md](MASTER_PLAN.md) for the current work program and [docs/NORTH_STAR.md](docs/NORTH_STAR.md) for the vision and goals.

| Document | Purpose |
|----------|---------|
| [NORTH_STAR.md](docs/NORTH_STAR.md) | Vision, goals, guiding principles |
| [synthesis.md](docs/synthesis.md) | Full problem statement and design rationale |
| [novel-capabilities.md](docs/novel-capabilities.md) | What's novel vs. existing tools |
| [architecture.md](docs/architecture.md) | Layer mapping: what to build vs. reuse |
| [revisions-and-open-design-spaces.md](docs/revisions-and-open-design-spaces.md) | Premature decisions corrected, open questions |
| [testing-strategy.md](docs/testing-strategy.md) | pytest + skill eval strategy |

## Contributing

All changes come through Pull Requests against `main`. Branch protection requires PR review before merge.

## License

MIT
