# State Cartographer: Project Layout and Bootstrap Guide

## What This Project Is

This is a **Claude Code plugin** under active development. The deliverables are skills, agents, commands, rules, and supporting Python scripts that together form a plugin called `state-cartographer`.

**This is not a traditional software application.** There is no app to run, no server to start, no UI to launch. The "product" is a set of markdown files and Python scripts that extend Claude Code's capabilities. The repo is the development environment for iterating on those files.

When an agent is working in this repo, it is **editing the plugin itself**, not using the plugin to automate something. The plugin's end users are other Claude Code sessions that will install the plugin and use it to build state graphs of external systems.

---

## Repository Structure

```
state-cartographer/
│
├── CLAUDE.md                         # Instructions for agents working ON this project
├── AGENTS.md                         # Agent definitions for working ON this project (dev agents)
├── README.md                         # Public-facing: what this plugin does, how to install
├── LICENSE
├── .gitignore
│
├── docs/                             # Design documents and conversation artifacts
│   ├── synthesis.md                  # Original conversation synthesis (the problem statement)
│   ├── novel-capabilities.md         # Enumeration of what's novel vs existing
│   ├── architecture.md              # Layer mapping and architectural decisions
│   └── decisions/                    # ADRs (Architecture Decision Records)
│       └── 001-python-over-typescript.md
│
├── plugin/                           # *** THE PRODUCT — everything below here IS the plugin ***
│   │
│   ├── skills/
│   │   ├── state-graph-authoring/
│   │   │   ├── SKILL.md              # Playbook for building/editing state graphs
│   │   │   └── references/
│   │   │       ├── schema.md         # Full schema extension spec (anchors, costs, etc.)
│   │   │       ├── consolidator.md   # Deep instructions for consolidation decisions
│   │   │       └── troubleshooting.md
│   │   │
│   │   └── state-graph-navigation/
│   │       ├── SKILL.md              # Playbook for runtime orientation and traversal
│   │       └── references/
│   │           └── pathfinding.md    # Pathfinding algorithm details and options
│   │
│   ├── agents/
│   │   ├── explorer.md               # Subagent: vision-heavy systematic navigation
│   │   ├── consolidator.md           # Subagent: observation analysis, anchor identification
│   │   └── optimizer.md              # Subagent: transition replacement analysis
│   │
│   ├── commands/
│   │   ├── explore.md                # /cartographer:explore
│   │   ├── consolidate.md            # /cartographer:consolidate
│   │   ├── optimize.md               # /cartographer:optimize
│   │   ├── locate.md                 # /cartographer:locate
│   │   └── status.md                 # /cartographer:status
│   │
│   ├── rules/
│   │   ├── safety.md                 # Confidence thresholds, irreversible action guards
│   │   ├── orientation.md            # Confirm state after transition, flag unknowns
│   │   └── graph-maintenance.md      # Flag unrecognized observations
│   │
│   └── scripts/                      # Python tooling called by skills and agents
│       ├── locate.py                 # Passive state classifier
│       ├── pathfind.py               # Weighted route planner (Dijkstra/A*)
│       ├── session.py                # Session state manager
│       ├── mock.py                   # Screenshot mock capture and validation
│       ├── graph_utils.py            # pytransitions wrapper for common queries
│       ├── schema_validator.py       # Validates graph definitions against the extended schema
│       └── requirements.txt          # pytransitions, pillow, imagehash, etc.
│
├── tests/                            # Tests for the Python scripts
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── sample-graph.json         # A complete example graph definition
│   │   ├── sample-session.json       # A sample session history
│   │   └── screenshots/              # Sample screenshots for mock testing
│   ├── test_locate.py
│   ├── test_pathfind.py
│   ├── test_session.py
│   ├── test_mock.py
│   ├── test_graph_utils.py
│   └── test_schema_validator.py
│
├── examples/                         # Example graph definitions for reference
│   ├── simple-web-form/
│   │   ├── graph.json                # A multi-step web form
│   │   └── README.md                 # Walkthrough of how this graph was built
│   └── template/
│       ├── graph.json                # Starter template with annotated comments
│       └── README.md
│
└── dev/                              # Development utilities (NOT part of the plugin)
    ├── install-local.sh              # Symlink plugin/ into ~/.claude/ for local testing
    ├── uninstall-local.sh
    ├── package.sh                    # Package plugin/ into a .skill or distributable
    └── lint-skills.sh                # Check SKILL.md frontmatter, reference links, etc.
```

---

## Key Distinctions the Working Agent Must Understand

### The `plugin/` directory is the product

Everything inside `plugin/` will be distributed to end users. Changes here directly affect what users of the plugin experience. Markdown quality, script reliability, progressive disclosure structure all matter here.

### Everything outside `plugin/` is development infrastructure

`docs/`, `tests/`, `examples/`, `dev/` are for our use while building the plugin. They don't ship. They can be messy, experimental, in-progress.

### There are two kinds of agents in this project

1. **Dev agents** (defined in the root `AGENTS.md`): agents that work on building/improving the plugin itself. These are us, right now.
2. **Plugin agents** (defined in `plugin/agents/`): agents that end users invoke when using the plugin to automate external systems. These are the product.

Do not confuse them. When editing `plugin/agents/explorer.md`, you are writing instructions for a *future agent that will explore external systems*. You are not that agent.

### There are two kinds of CLAUDE.md

1. **Root `CLAUDE.md`**: instructions for agents working in this repo to develop the plugin. Contains: repo structure, coding conventions, testing instructions, what not to break.
2. **No CLAUDE.md inside `plugin/`**: the plugin's instructions live in its SKILL.md files and agent definitions. It does not have its own CLAUDE.md because it will be installed into users' projects which have their own.

---

## CLAUDE.md Content (for root)

```markdown
# State Cartographer — Development Instructions

## What this project is

This repo contains a Claude Code plugin called state-cartographer. The plugin
helps agents build queryable state graphs of external systems they're automating.
Everything in plugin/ is the deliverable. Everything else is dev infrastructure.

## Project structure

- plugin/           — THE PRODUCT. Skills, agents, commands, rules, scripts.
- docs/             — Design docs and architecture decisions. Read these first.
- tests/            — pytest tests for scripts in plugin/scripts/.
- examples/         — Example graph definitions for reference and testing.
- dev/              — Dev utilities (local install, packaging, linting).

## When working on this project

- Read docs/synthesis.md and docs/novel-capabilities.md for full context on
  what this plugin does and why.
- Read docs/architecture.md for the layer mapping and design decisions.
- The Python scripts in plugin/scripts/ are the hard tooling. They must have
  tests. Run: pytest tests/ -v
- The markdown files in plugin/skills/, plugin/agents/, plugin/commands/,
  plugin/rules/ are the methodology. They must be clear, opinionated, and
  follow progressive disclosure (SKILL.md under 500 lines, deeper content
  in references/).
- Do not confuse "dev agents" (us, working on the plugin) with "plugin agents"
  (explorer.md, consolidator.md, optimizer.md — these are the product).
- Python style: type hints, docstrings, no classes where functions suffice.
- Dependencies go in plugin/scripts/requirements.txt.
- Graph definitions use JSON. The schema extends standard state machine
  config with observation anchors, transition costs, wait state annotations,
  and confidence thresholds. See docs/architecture.md Layer 1.

## Testing

pytest tests/ -v

To test the plugin locally in a real Claude Code session:
bash dev/install-local.sh

## Key files to read first

1. docs/synthesis.md — the full problem statement
2. docs/novel-capabilities.md — what's novel vs what exists
3. docs/architecture.md — layer mapping, capability assignments
4. plugin/skills/state-graph-authoring/SKILL.md — the main playbook (once written)
```

---

## First-Time Setup Instructions

These are the steps to bootstrap the repo from scratch.

### 1. Initialize the repository

```bash
mkdir state-cartographer && cd state-cartographer
git init
```

### 2. Create the directory skeleton

```bash
# Product directories
mkdir -p plugin/skills/state-graph-authoring/references
mkdir -p plugin/skills/state-graph-navigation/references
mkdir -p plugin/agents
mkdir -p plugin/commands
mkdir -p plugin/rules
mkdir -p plugin/scripts

# Dev infrastructure
mkdir -p docs/decisions
mkdir -p tests/fixtures/screenshots
mkdir -p examples/simple-web-form
mkdir -p examples/template
mkdir -p dev
```

### 3. Copy design documents from conversation artifacts

The three markdown files produced during the design conversation should be placed:

```bash
cp state-machine-tooling-synthesis.md    docs/synthesis.md
cp novel-capabilities-enumeration.md     docs/novel-capabilities.md
cp architecture-layer-mapping.md         docs/architecture.md
```

These are the project's foundational design documents. Any agent working in this repo should read them before making significant changes.

### 4. Create the CLAUDE.md

Use the content from the "CLAUDE.md Content" section above.

### 5. Create .gitignore

```gitignore
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
.venv/
venv/
*.session.json
node_modules/
.DS_Store
```

### 6. Set up Python environment

```bash
cd plugin/scripts
cat > requirements.txt << 'EOF'
transitions>=0.9.0
Pillow>=10.0.0
imagehash>=4.3.0
EOF

cd ../..
python -m venv .venv
source .venv/bin/activate
pip install -r plugin/scripts/requirements.txt
pip install pytest
```

### 7. Create placeholder files for all plugin components

Every file that should exist gets created with a header comment explaining what it will contain. This gives the agent a map of what needs to be written.

```bash
# Skills
touch plugin/skills/state-graph-authoring/SKILL.md
touch plugin/skills/state-graph-authoring/references/schema.md
touch plugin/skills/state-graph-authoring/references/consolidator.md
touch plugin/skills/state-graph-authoring/references/troubleshooting.md
touch plugin/skills/state-graph-navigation/SKILL.md
touch plugin/skills/state-graph-navigation/references/pathfinding.md

# Agents
touch plugin/agents/explorer.md
touch plugin/agents/consolidator.md
touch plugin/agents/optimizer.md

# Commands
touch plugin/commands/explore.md
touch plugin/commands/consolidate.md
touch plugin/commands/optimize.md
touch plugin/commands/locate.md
touch plugin/commands/status.md

# Rules
touch plugin/rules/safety.md
touch plugin/rules/orientation.md
touch plugin/rules/graph-maintenance.md

# Scripts
touch plugin/scripts/locate.py
touch plugin/scripts/pathfind.py
touch plugin/scripts/session.py
touch plugin/scripts/mock.py
touch plugin/scripts/graph_utils.py
touch plugin/scripts/schema_validator.py

# Tests
touch tests/conftest.py
touch tests/test_locate.py
touch tests/test_pathfind.py
touch tests/test_session.py
touch tests/test_mock.py
touch tests/test_graph_utils.py
touch tests/test_schema_validator.py

# Examples
touch examples/template/graph.json
touch examples/template/README.md
touch examples/simple-web-form/graph.json
touch examples/simple-web-form/README.md

# Dev utilities
touch dev/install-local.sh
touch dev/uninstall-local.sh
touch dev/package.sh
touch dev/lint-skills.sh
```

### 8. Create the example graph template

`examples/template/graph.json` should contain a minimal but complete graph definition demonstrating all schema extensions (anchors, costs, wait states, confidence thresholds) with inline comments explaining each field. This serves as the canonical example that both developers and the plugin's end users reference.

### 9. Initial commit

```bash
git add -A
git commit -m "feat: scaffold state-cartographer plugin

Bootstrap repository structure for the state-cartographer Claude Code plugin.

Product deliverables live in plugin/ (skills, agents, commands, rules, scripts).
Design documents from the original conversation are in docs/.
Dev infrastructure in tests/, examples/, dev/.

See docs/synthesis.md for full problem statement.
See docs/novel-capabilities.md for what's novel.
See docs/architecture.md for layer mapping."
```

### 10. Create a GitHub repo and push

```bash
git remote add origin git@github.com:<user>/state-cartographer.git
git branch -M main
git push -u origin main
```

---

## Build Order Recommendation

After bootstrap, the recommended order for building out the plugin:

### Sprint 1: Schema and Core Tooling
1. **`docs/decisions/001-python-over-typescript.md`** — formalize the runtime language decision
2. **`plugin/skills/state-graph-authoring/references/schema.md`** — the full schema spec. This is the foundation everything else depends on.
3. **`examples/template/graph.json`** — canonical example implementing the schema
4. **`plugin/scripts/graph_utils.py`** + tests — pytransitions wrapper, graph loading, basic queries
5. **`plugin/scripts/schema_validator.py`** + tests — validates graph definitions against the schema

### Sprint 2: Runtime Tools
6. **`plugin/scripts/session.py`** + tests — session manager
7. **`plugin/scripts/locate.py`** + tests — the passive state classifier (the core novel tool)
8. **`plugin/scripts/pathfind.py`** + tests — weighted route planner

### Sprint 3: Skills and Playbook
9. **`plugin/skills/state-graph-navigation/SKILL.md`** — runtime skill (how to use locate, pathfind, session during automation)
10. **`plugin/skills/state-graph-authoring/SKILL.md`** — authoring skill (the full methodology playbook)
11. **Reference docs** for both skills

### Sprint 4: Agents, Commands, Rules
12. **`plugin/agents/explorer.md`** — exploration subagent definition
13. **`plugin/agents/consolidator.md`** — consolidation subagent definition
14. **`plugin/agents/optimizer.md`** — optimization subagent definition
15. **`plugin/commands/`** — all five command definitions
16. **`plugin/rules/`** — all three rule definitions
17. **`plugin/scripts/mock.py`** + tests — screenshot mock manager

### Sprint 5: Polish and Package
18. **`examples/simple-web-form/`** — a worked example showing the full workflow
19. **`dev/install-local.sh`** and **`dev/package.sh`** — packaging and local testing
20. **`README.md`** — public-facing documentation
21. **`dev/lint-skills.sh`** — validation that all SKILL.md files have proper frontmatter, all references/ files are linked, all scripts have tests

---

## Notes for the First Agent Session

When an agent first opens this repo after bootstrap, it should:

1. Read `CLAUDE.md` (will be loaded automatically)
2. Read `docs/synthesis.md` to understand the problem this plugin solves
3. Read `docs/novel-capabilities.md` to understand what's novel vs what exists
4. Read `docs/architecture.md` to understand the layer mapping
5. Look at the sprint 1 items and start with the schema spec

The agent should NOT:
- Try to build the entire plugin in one session
- Start with SKILL.md before the schema and core tools exist (the playbook references tools that need to exist first)
- Confuse itself with the end-user agents (explorer, consolidator, optimizer) — those are the product, not the dev workflow
- Install or use the plugin to automate an external system — the plugin doesn't exist yet; we're building it
