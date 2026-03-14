# State Cartographer: Testing Strategy

## Two Kinds of Testing, Don't Confuse Them

This project requires two fundamentally different testing approaches that operate at different layers and test different things:

1. **Python unit/integration tests** for the scripts in `scripts/`. These are traditional pytest tests. They test whether `locate.py` returns the correct state given known inputs, whether `pathfind.py` computes the cheapest route, whether `session.py` tracks history correctly. These are deterministic, fast, and run in CI.

2. **Skill evals** for the SKILL.md files, agents, commands, and rules. These test whether Claude actually uses the skill correctly when given realistic prompts. Does the skill trigger when it should? Does the agent follow the playbook? Does the output match expectations? These are LLM-evaluated, slower, and run via the skill-creator eval framework.

Both are necessary. Neither substitutes for the other. A perfectly tested `locate.py` is useless if the SKILL.md gives bad instructions for when to call it. A beautifully written SKILL.md is useless if `locate.py` returns wrong answers.

---

## Layer 1: Python Script Tests (pytest)

### What we're testing

Every script in `scripts/` gets conventional pytest tests. These are the deterministic tools that do real work.

### Test structure

```
tests/
├── conftest.py                    # Shared fixtures
├── fixtures/
│   ├── graphs/
│   │   ├── simple-linear.json     # A → B → C → D, no branching
│   │   ├── branching.json         # A → B|C, B → D, C → D
│   │   ├── with-anchors.json      # Full schema: anchors, costs, wait states
│   └── graphs/
│       ├── simple-linear.json     # A → B → C → D, no branching
│       ├── branching.json         # A → B|C, B → D, C → D
│       └── with-anchors.json      # Full schema: anchors, costs, wait states
├── test_graph_utils.py
├── test_adb_bridge.py
├── test_calibrate.py
├── test_integration.py
├── test_schema_validator.py
├── test_session.py
├── test_locate.py
├── test_observe.py
├── test_pathfind.py
└── test_mock.py
```

### What each test file covers

**`test_graph_utils.py`** — graph loading, state enumeration, transition queries
- Load a valid graph, list all states
- Query valid transitions from a specific state
- Query reachable states within N hops
- Identify orphan states (no inbound)
- Identify states missing anchors
- Handle malformed graph gracefully (clear error, not crash)

**`test_schema_validator.py`** — validates extended schema fields
- Accept valid graph with all extensions
- Reject graph missing required anchor fields
- Reject graph with unknown anchor types
- Reject transition with invalid cost values
- Reject wait state missing exit signals
- Reject confidence threshold outside 0-1 range
- Provide clear error messages pointing to the specific problem

**`test_session.py`** — session lifecycle
- Init creates valid session
- Confirm state updates history
- Record transition updates history
- Query returns current state and history
- Session history constrains candidate states correctly
- Session handles restart (new session from known state)

**`test_locate.py`** — the core classifier, most important tests
- Given clear-match observations + empty session → returns correct state with high confidence
- Given clear-match observations + confirming session history → returns correct state with very high confidence
- Given ambiguous observations + empty session → returns candidate set with disambiguation probes
- Given ambiguous observations + constraining session history → narrows candidates (session breaks the tie)
- Given no-match observations → returns unknown state with escalation recommendation
- Given partial observations → returns candidates ranked by number of matching anchors
- Anchors evaluated in cost order (cheapest first)
- Negative anchors prune candidates
- Confidence thresholds respected (high-threshold states require stronger evidence)

**`test_pathfind.py`** — weighted route planning
- Shortest path in a linear graph
- Cheapest path when shorter path is more expensive
- Path avoidance (route around a specified state)
- Prefer-deterministic flag biases toward cheap transitions
- No path exists → clear error
- Current state equals target → empty path (no-op)
- Handles cycles without infinite loop

**`test_mock.py`** — screenshot mock management
- Capture associates screenshot with state
- Validate runs anchors against screenshots, reports coverage
- Test-locate runs classifier against known-state screenshot
- Reports which states have no screenshots
- Reports which anchors fail against their state's screenshots

### Running tests

```bash
# All tests
pytest tests/ -v

# Just one module
pytest tests/test_locate.py -v

# With coverage
pytest tests/ --cov=scripts --cov-report=html
```

### CI integration

Standard GitHub Actions workflow:

```yaml
# .github/workflows/test.yml
name: Test Scripts
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install uv
      - run: uv venv
      - run: uv pip install -e ".[dev]"
      - run: pytest tests/ -v --cov=scripts
```

---

## Layer 2: Skill Evals (skill-creator framework)

### What we're testing

Whether the SKILL.md files, agents, commands, and rules actually work when Claude uses them. This is the layer Anthropic updated in March 2026 with the skill-creator 2.0 eval framework.

### How skill evals work

The skill-creator operates in four modes: **Create**, **Eval**, **Improve**, **Benchmark**. For our purposes, Eval and Benchmark are the testing modes.

The eval pipeline uses four composable sub-agents:
- **Executor**: runs the skill against eval prompts (Claude with the skill loaded)
- **Grader**: evaluates outputs against defined expectations
- **Comparator**: performs blind A/B comparisons between skill versions
- **Analyzer**: surfaces patterns that aggregate stats might hide

### What we need to eval

We have two skills, three agents, five commands, and three rules. Each needs different eval approaches.

#### Skill: state-graph-authoring

**Trigger evals** — does the skill activate when it should?

```json
{
  "should_trigger": [
    "I need to build a state machine for the checkout flow on this ecommerce site",
    "Help me map out all the screens in this mobile app so I can automate it",
    "I've been automating this game UI and I keep getting lost, can we build a proper state graph?",
    "I have screenshots of every screen in this app, let's turn them into an automation-friendly format",
    "My browser automation keeps failing because it doesn't know what screen it's on"
  ],
  "should_not_trigger": [
    "Help me implement a state machine in my React app",
    "What's the best state management library for Python?",
    "Can you review this XState code?",
    "Write a finite state machine for parsing this regex",
    "How do I use pytransitions?"
  ]
}
```

The critical distinction in the trigger evals: this skill is about modeling **external** systems for automation, not about implementing state machines in your own code. The should-not-trigger cases are conventional state machine development tasks that existing tools handle fine.

**Output evals** — when the skill runs, does it produce correct results?

These require graph fixture files. Given an example graph and a task ("add observation anchors to the login screen state"), does the output conform to the schema? Does it include cost annotations? Are the anchors plausibly stable?

#### Skill: state-graph-navigation

**Trigger evals** — activates during automation when the agent needs to orient or route.

```json
{
  "should_trigger": [
    "I'm automating this app and I think the page changed since last time, where am I?",
    "I need to get from the settings screen to the payment screen, what's the fastest path?",
    "My automation crashed mid-task, how do I figure out where I left off?",
    "The screen doesn't match what I expected after clicking that button"
  ],
  "should_not_trigger": [
    "Build me a state graph for this website",
    "What states should I add to model this checkout flow?",
    "Help me set up the exploration agent for a new app"
  ]
}
```

**Output evals** — does it call the right scripts with the right arguments?

Given a graph, a session, and a simulated observation, does the skill correctly invoke `locate.py`? Does it interpret the results correctly? When locate returns ambiguity, does it follow the disambiguation protocol rather than guessing?

#### Agent evals

Agent evals are harder because agents are subagents with their own execution context. The approach:

1. Set up a test scenario with a known graph and mock observations
2. Invoke the agent (e.g., the consolidator) with a specific task
3. Grade whether the output matches expectations

For the **explorer agent**: given a mock environment (simulated screenshots), does it systematically navigate rather than randomly? Does it record observations in the correct format? Does it detect when it's revisited a known state?

For the **consolidator agent**: given a set of raw observations from the explorer, does it correctly identify state boundaries? Does it propose reasonable anchors? Does it flag ambiguous cases for human review?

For the **optimizer agent**: given a completed graph with all-vision transitions, does it identify which transitions could be replaced with deterministic calls? Does it propose reasonable replacements?

#### Rule evals

Rules need negative testing: set up a scenario where the rule should prevent an action, and verify it does.

- **safety.md**: present a low-confidence state classification for an irreversible action. Does Claude refuse to proceed and request vision review?
- **orientation.md**: execute a transition. Does Claude call locate() to confirm arrival? If it doesn't match expected state, does it flag rather than continue?
- **graph-maintenance.md**: present observations that don't match any state in the graph. Does Claude flag this rather than ignoring it?

### Eval file location

```
evals/
├── trigger-evals/
│   ├── authoring-skill.json
│   └── navigation-skill.json
├── output-evals/
│   ├── authoring-scenarios.json
│   └── navigation-scenarios.json
├── agent-evals/
│   ├── explorer-scenarios.json
│   ├── consolidator-scenarios.json
│   └── optimizer-scenarios.json
├── rule-evals/
│   ├── safety-scenarios.json
│   ├── orientation-scenarios.json
│   └── graph-maintenance-scenarios.json
└── benchmarks/
    └── baseline-results.json      # Recorded results for regression detection
```

### Running skill evals

Within Claude Code, using the skill-creator plugin:

```
/skill-creator eval --skill-path skills/state-graph-authoring --eval-set evals/trigger-evals/authoring-skill.json
```

Or for benchmarking (multiple runs with variance analysis):

```
/skill-creator benchmark --skill-path skills/state-graph-authoring --eval-set evals/output-evals/authoring-scenarios.json --runs 5
```

### When to run what

| Situation | Python tests | Skill evals |
|---|---|---|
| Changed a script in scripts/ | Yes (pytest) | Maybe (if the change affects how the skill calls the script) |
| Changed a SKILL.md | No | Yes (trigger + output evals) |
| Changed an agent definition | No | Yes (agent evals) |
| Changed a rule | No | Yes (rule evals) |
| Changed the schema spec | Yes (validator tests) | Yes (authoring output evals) |
| Model update (new Claude version) | No (deterministic code doesn't care) | Yes (all evals; this is the main regression risk) |
| Before a release | Yes (full suite) | Yes (full benchmark) |

---

## The Iteration Loop

The practical workflow for developing and testing any component:

### For scripts (locate.py, pathfind.py, etc.)

1. Write/edit the script
2. Write/update pytest tests
3. Run `pytest tests/test_<script>.py -v`
4. Fix failures
5. When green, commit
6. If the script's behavior affects skill output, also run relevant skill evals

### For skills (SKILL.md)

This follows the skill-creator loop from Anthropic's framework:

1. Draft or edit the SKILL.md
2. Write eval prompts (realistic, specific, edge-case-heavy)
3. Run evals via skill-creator (executor → grader)
4. Review results with the human via eval-viewer
5. Iterate on the SKILL.md based on failures
6. When passing, run a benchmark (5+ runs with variance analysis) to confirm stability
7. Optionally run trigger optimization (60/40 train/test split on description)
8. Commit

### For agents

1. Draft agent definition
2. Write agent eval scenarios
3. Run evals (these are slower; agents have their own subagent context)
4. Review: did the agent follow its instructions? Did it produce correctly structured output?
5. Iterate
6. Commit

### For rules

1. Draft rule
2. Write negative test scenarios (situations where the rule should prevent action)
3. Run rule evals
4. Verify: did Claude respect the rule? If not, is the rule wording ambiguous?
5. Iterate
6. Commit

---

## What "Done" Looks Like

A component is ready for release when:

- **Scripts**: all pytest tests pass, coverage is above 80% for core logic (locate, pathfind, session)
- **Skills**: trigger eval accuracy above 85% (fires when it should, doesn't fire when it shouldn't), output evals pass on all primary scenarios, benchmark shows consistent results across 5+ runs
- **Agents**: agent eval scenarios pass, outputs conform to expected structure, human review confirms the agent follows the methodology
- **Rules**: negative test scenarios confirm the rule prevents unwanted actions, no false positives on normal operations

Regression baseline: before any release, run the full benchmark suite and record results. After model updates or significant changes, re-run and compare. This is the main guard against the silent degradation problem that skill-creator 2.0 was built to solve.
