# Issue #1: Define the Environment Integration Contract

## Priority: High — blocks real-world usage

## Problem

The state-cartographer pipeline (locate, pathfind, session, mock, exploration agents) needs to observe and act on an external system. But the *means* of observing and acting will be completely different for every project:

- ALAS (Azur Lane automation): ADB screenshots, ADB tap input, MaaTouch for fast input, existing Python process with device connection already established
- Web automation: Playwright or Selenium, DOM access, URL navigation
- Desktop app: accessibility APIs, window screenshots, keyboard/mouse injection
- CLI tool: stdout/stderr capture, stdin injection
- Some future thing we haven't imagined

We must NOT bake any specific integration into the pipeline. We must NOT require users to install ADB or Playwright if they already have their own tooling.

## What We Need

A clearly documented **contract** that specifies exactly what the pipeline expects at each boundary. Not an abstract base class or a formal adapter framework (at least not yet). Just a dead-simple spec that says:

### Observation capabilities the pipeline consumes

| Capability | Input | Output | Required? | Used by |
|---|---|---|---|---|
| Capture screenshot | (none) | PNG bytes or file path | Yes (for exploration; optional at runtime if anchors are non-visual) | explorer agent, mock.py, locate.py (fallback) |
| Check pixel color | x: int, y: int | (r, g, b) tuple | Optional | locate.py (pixel-type anchors) |
| Read text from region | bbox: (x1, y1, x2, y2) | string | Optional | locate.py (text-type anchors) |
| Check element presence | selector: string (format TBD) | bool | Optional (web/DOM only) | locate.py (dom-type anchors) |
| Get screen dimensions | (none) | (width, height) | Yes | pathfind.py (coordinate validation), mock.py |

### Action capabilities the pipeline consumes

| Capability | Input | Output | Required? | Used by |
|---|---|---|---|---|
| Tap/click at coordinates | x: int, y: int | success: bool | Yes | pathfind.py (deterministic transitions), explorer agent |
| Swipe | x1, y1, x2, y2, duration_ms | success: bool | Optional | transitions that involve scrolling |
| Press back/escape | (none) | success: bool | Optional but strongly recommended | disambiguation probes, navigation |
| Input text | text: string | success: bool | Optional | transitions that involve text entry |
| Wait | duration_ms: int | (none) | Yes | wait states |

### How the contract gets fulfilled

The expectation is NOT that we build a formal plugin/adapter system. The expectation is:

1. The contract is documented clearly in the skill's references (probably `references/integration.md`)
2. When someone invokes the skill in a new project, the **first thing the skill tells the agent to do** is: "Look at the existing project. Find the existing ways to take screenshots and inject input. Write a small Python module (`cartographer_env.py` or whatever) that wraps them into the functions the pipeline expects. Test it: can you take a screenshot? Can you tap? Good, proceed."
3. The agent (Claude Code, or whatever) is perfectly capable of reading the contract, reading the existing codebase, and writing the glue code. This is exactly the kind of integration work LLMs are good at.

## What This Means for Phase 0

The SKILL.md needs a Phase 0 before exploration begins:

**Phase 0: Connect to the environment**
- What system are you automating?
- Look at the existing project for observation capabilities (screenshot, pixel check, text read, DOM query)
- Look at the existing project for action capabilities (tap, swipe, back, text input)
- Write the integration module that exposes these in the format the pipeline expects
- Test: take a screenshot, execute a tap, confirm both work
- Only then proceed to Phase 1 (exploration)

## What This Means for the Scripts

Each script in `plugin/scripts/` needs to accept its inputs in a way that doesn't assume a specific backend:

- `locate.py` takes observation data as JSON (screenshot path, pixel values, text matches, element presence), NOT raw ADB output
- `pathfind.py` returns a sequence of abstract actions (`{"type": "tap", "x": 450, "y": 800}`) that the integration module executes
- `session.py` records state confirmations and transitions, doesn't interact with the environment at all
- `mock.py` takes screenshot file paths, doesn't capture screenshots itself

The scripts are pure logic. The integration module is the bridge between the scripts and the real environment. The agent writes the integration module.

## Acceptance Criteria

- [ ] `references/integration.md` exists with the full contract table (observation + action capabilities, inputs, outputs, formats)
- [ ] Each script's docstring/README specifies exactly what input format it expects and what it returns
- [ ] The SKILL.md includes Phase 0 (environment connection) before Phase 1 (exploration)
- [ ] An example integration module exists in `examples/` showing what one looks like for ADB (even if it's pseudocode/sketch, not runnable)
- [ ] The contract is simple enough that an agent reading it + reading an unfamiliar codebase can write the integration module in one pass

## Non-Goals

- We are NOT building a formal adapter/plugin framework with abstract base classes and registration
- We are NOT bundling ADB, Playwright, Appium, or any specific tooling
- We are NOT making the integration module auto-discoverable or auto-generated (the agent writes it, that's fine)
- We may revisit these decisions later if the pattern proves too brittle, but for now, simplicity wins

## Labels

`documentation`, `architecture`, `high-priority`
