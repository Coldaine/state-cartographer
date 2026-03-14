# State Cartographer

A Claude Code plugin and toolkit for building, maintaining, and navigating queryable state graphs of external systems. Enables AI agents to map unfamiliar interfaces, orient themselves from observations alone, and navigate via the cheapest available path.

## What This Is

When an AI agent automates an external system (web app, mobile game, desktop application), it has no model of that system. It sees pixels, reasons about them, clicks, waits, and repeats. This works but is slow, expensive, and fragile.

State Cartographer provides:

- **A schema** extending standard state machine formats with observation anchors, transition costs, wait state annotations, and confidence thresholds
- **Runtime tools** (`locate`, `pathfind`, `session`) for deterministic state classification and weighted route planning
- **A methodology/playbook** for LLM-driven graph construction from exploration
- **Multi-agent decomposition** across graph construction and maintenance phases

The state graph becomes an API for a system that never published one.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/Coldaine/state-cartographer.git
cd state-cartographer

# Install with UV (creates .venv automatically)
uv sync

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

See [docs/NORTH_STAR.md](docs/NORTH_STAR.md) for the vision and goals.

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
