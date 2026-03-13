# AGENTS.md — Documentation Index

> This file is the mandatory starting point. Read this before anything else.

## Required Reading (Start Here)

| Document | What It Covers |
|----------|---------------|
| [plan.md](plan.md) | Master plan: development phases, key workflows, success metrics |
| [CLAUDE.md](CLAUDE.md) | Project conventions, commands, coding standards for Claude Code |
| [docs/NORTH_STAR.md](docs/NORTH_STAR.md) | Vision, goals, guiding principles, open questions |
| [docs/architecture.md](docs/architecture.md) | 5-layer architecture, capability-to-layer mapping |

## Design Documents

| Document | Topic |
|----------|-------|
| [docs/synthesis.md](docs/synthesis.md) | State machine tooling synthesis — survey of existing tools and how they fit |
| [docs/novel-capabilities.md](docs/novel-capabilities.md) | Enumeration of capabilities no existing library provides (anchors, weighted pathfinding, etc.) |
| [docs/testing-strategy.md](docs/testing-strategy.md) | Testing approach: unit, integration, end-to-end, mock system |
| [docs/revisions-and-open-design-spaces.md](docs/revisions-and-open-design-spaces.md) | Open design decisions and areas needing resolution |
| [docs/decisions/001-python-over-typescript.md](docs/decisions/001-python-over-typescript.md) | ADR: Why Python instead of TypeScript |

## Plugin Structure

### Skills (Playbooks)

| Skill | Purpose |
|-------|---------|
| [skills/state-graph-authoring/SKILL.md](skills/state-graph-authoring/SKILL.md) | Core playbook: exploration → consolidation → optimization → maintenance |
| [skills/state-graph-navigation/SKILL.md](skills/state-graph-navigation/SKILL.md) | Using an existing graph for cheap navigation |

### Agents (Subagent Definitions)

| Agent | Role |
|-------|------|
| [agents/explorer.md](agents/explorer.md) | Vision-heavy BFS navigation, builds raw observation dataset |
| [agents/consolidator.md](agents/consolidator.md) | Analyzes observations, chooses anchors, produces graph.json |
| [agents/optimizer.md](agents/optimizer.md) | Replaces vision transitions with deterministic alternatives |

### Rules (Always-On)

| Rule | Governs |
|------|---------|
| [rules/safety.md](rules/safety.md) | Confidence tiers, irreversible action guards, escalation paths |
| [rules/orientation.md](rules/orientation.md) | State confirmation after transitions, disambiguation, recovery |
| [rules/graph-maintenance.md](rules/graph-maintenance.md) | When and how to update the graph during operation |

### Scripts (Runtime Tools)

| Script | Function |
|--------|----------|
| `scripts/locate.py` | Passive state classifier — “where am I?” |
| `scripts/pathfind.py` | Weighted route planner — “how do I get there?” |
| `scripts/session.py` | Session state manager — tracks confirmed states and transitions |
| `scripts/graph_utils.py` | Graph inspection utilities — list states, find orphans, check reachability |
| `scripts/schema_validator.py` | Schema validator — checks graph.json integrity |
| `scripts/screenshot_mock.py` | Mock/screenshot manager — capture and validate against graph |

### References

| Reference | Content |
|-----------|---------|
| [skills/state-graph-authoring/references/schema.md](skills/state-graph-authoring/references/schema.md) | Complete graph.json schema specification |

## Examples

| Example | Description |
|---------|-------------|
| [examples/template/](examples/template/) | Starter 3-state graph template with README |

## Project Meta

| File | Purpose |
|------|---------|
| [README.md](README.md) | Project overview for GitHub |
| [LICENSE](LICENSE) | MIT License |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | CI pipeline: pytest on Python 3.11/3.12/3.13 |
| [docs/bootstrap.md](docs/bootstrap.md) | Original bootstrap instructions (historical reference) |
