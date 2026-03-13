# Revisions and Open Design Spaces

This document flags places where existing project docs made premature decisions, and addresses concerns that weren't sufficiently covered.

---

## Premature Decisions to Relax

### 1. "Python with pytransitions" is not decided

The architecture doc recommends Python with pytransitions as the graph engine. This was stated as a recommendation but reads like a decision. In reality:

- We haven't built anything yet
- We haven't validated that pytransitions' introspection API actually covers our needs for the extended schema
- We haven't tested whether XState's JSON format is actually a good interchange format
- The user environment might involve TypeScript tooling (Gemini CLI, other LLM tools)

**Revision**: the architecture doc should present this as an open question with tradeoffs, not a recommendation. The first sprint should include a spike to test both pytransitions and at least one other option against the actual requirements of `locate()` and `pathfind()`.

### 2. Multi-agent decomposition is aspirational, not confirmed

The project layout proposes three subagents (explorer, consolidator, optimizer) as distinct agent definitions. This may be the right architecture, but we don't know yet:

- We haven't validated that subagents are the right primitive here (vs. commands, vs. skill phases, vs. just prompting)
- The overhead of spawning subagents may not be worth it for early iterations
- The boundaries between phases may turn out to be blurry in practice

**Revision**: the `plugin/agents/` directory stays in the layout as a target, but the first iterations should work as a single skill with phases, not as separate agents. Agent decomposition happens only after we've manually run the workflow enough times to know where the natural handoff points actually are.

### 3. The specific script interfaces are speculative

The architecture doc specifies CLI interfaces for `locate.py`, `pathfind.py`, etc. with specific flags and JSON formats. These are reasonable guesses but haven't been tested:

- The `--observations obs.json` input format assumes we know what observations look like before we've done any exploration
- The output format for `locate()` assumes we know what disambiguation looks like before we've encountered ambiguity

**Revision**: the script interfaces should be designed after the first exploration pass against a real system, not before. The first version of `locate.py` will probably be ugly and specific to the test system. That's fine. Generalize from working code, not from imagined interfaces.

### 4. The testing strategy assumes we know what to test

The testing doc has detailed fixture structures and test cases for scripts that don't exist yet. This is useful as a target but shouldn't constrain the implementation:

- Test cases for `locate.py` assume we know what observation data looks like
- Test cases for `pathfind.py` assume we know what the cost model looks like

**Revision**: write tests after the first working prototype, not before. The test fixtures should come from real data captured during the first exploration, not from imagined scenarios. TDD is wrong here; discover-then-test is right.

### 5. The plugin structure may be premature

The project layout proposes a full plugin with skills, agents, commands, and rules. This is the end state, but starting with a full plugin structure before we have working tooling adds overhead without benefit:

- We might iterate faster with a flat directory and a single SKILL.md
- The plugin packaging and installation workflow is unnecessary until the tools actually work

**Revision**: start with a flat working directory. Refactor into plugin structure once the core tools (locate, pathfind, session, graph utils) are working and have been tested against a real system.

---

## Observation Gathering: The Piggyback Problem

The biggest practical question for Phase 1 is: how do we get enough data to build a state graph in the first place?

The answer isn't always "run an expensive vision agent and let it explore." Often the user already has automation running. In the ALAS case, the existing automation already navigates the game menus, takes screenshots, and executes actions. The state cartographer should be able to **piggyback on that existing automation** to gather observations without disrupting it.

This means the very first capability isn't "explore" but "observe and record." Something that watches whatever is already happening and captures:

- Screenshots at regular intervals or on screen change detection
- Actions taken (taps, clicks, keystrokes) with timestamps
- Any state signals the existing automation already tracks

From this passive observation log, the state graph construction can begin offline. You don't need to drive the system to learn about it; you just need to watch someone (or something) else drive it.

This changes the Phase 1 description significantly. It's not always:

> "Point a vision agent at the system and let it navigate."

It's sometimes:

> "Attach to an existing automation and record what it does. Build the graph from the recording."

And sometimes:

> "The user manually uses the app for 30 minutes while we capture screenshots and actions. Build the graph from that."

The exploration agent is one path to gathering data. Passive observation of existing usage is another. Both produce the same raw material: timestamped sequences of observations and actions.

---

## Mock Harness: When Does It Become Possible?

The mock harness (offline development against captured screenshots) becomes possible as soon as you have:

1. A set of screenshots, each labeled with a state name
2. A graph definition that references those state names
3. Anchors defined for at least some of those states

At that point, you can run `locate()` against the screenshot dataset without the live system. You can validate whether your anchors correctly classify each screenshot. You can iterate on the graph definition and anchors without consuming any LLM tokens or needing the external system to be running.

The critical implication: **screenshot capture is the first thing that needs to work, before anything else.** The mock harness is what makes fast iteration possible. Without it, every test requires the live system, which is slow, expensive, and sometimes impractical.

The minimum viable mock harness is:

- A directory of screenshots named by state: `main_menu_01.png`, `dock_01.png`, `dock_02.png`
- A graph JSON with anchor definitions
- A script that runs each screenshot through the anchor evaluator and reports matches

This should be buildable before `locate()`, `pathfind()`, or any other tool is complete. It's the development scaffold that enables everything else.

---

## Multi-LLM Reality

This project is not Claude Code exclusive. In practice:

- **Claude Code** will likely be the primary development environment for building and iterating on the plugin itself
- **Gemini CLI** (or Gemini with vision) may be the tool used for the actual exploration phase, since it has strong vision capabilities and different cost characteristics
- **Other LLM tools** may be used for specific phases (optimization analysis, anchor validation, etc.)

The SKILL.md and methodology need to be written in a way that isn't Claude-specific. The playbook describes what to do, not which LLM to do it with. The scripts are Python and don't depend on any specific LLM runtime.

Where LLM-specific behavior matters (e.g., how to invoke vision analysis on a screenshot), the skill should describe the capability needed ("analyze this screenshot and describe the UI elements") rather than the specific tool call.

This also affects testing: skill evals via the skill-creator framework are Claude Code specific, but the Python script tests are universal. The methodology should be validatable regardless of which LLM is driving.

---

## Cross-Session Workflow Continuity

This project involves work that spans many sessions, potentially weeks. The state graph isn't built in one sitting. The natural workflow is:

- Session 1: set up environment connection, capture initial screenshots
- Session 2: start building the graph from captured data
- Session 3: refine state boundaries, add anchors
- Session 4: do a live exploration pass to discover states we missed
- Session 5: optimization pass on transitions
- ...and so on

Each session needs to know what happened in previous sessions. The existing primitives for this:

**CLAUDE.md / MEMORY.md**: Claude Code's built-in auto-memory writes session summaries to `~/.claude/projects/<hash>/<session>/session-memory/summary.md`. These are automatically loaded at session start. Good for general project context, but not structured enough for tracking specific graph construction progress.

**Session brief/start pattern**: A pattern using two skills: `/brief` at end of session writes a comprehensive handoff document capturing current state, decisions made, and next steps; `/start` at beginning of next session reads the brief and git state to orient. This is close to what we need.

**Progress log pattern**: Timestamped progress logs that preserve workflow state for crash recovery and accelerate handoffs between sessions. The key idea: progress logs are the "autosave" of the workflow.

For state-cartographer specifically, the cross-session continuity needs to track:

- **Graph construction progress**: which states have been discovered, which have anchors, which have transition cost annotations, which are still vision-only
- **Exploration coverage**: what parts of the external system have been visited, what's known to be unexplored
- **Open questions**: what state consolidation decisions are pending human input
- **Known issues**: which anchors have been flagged as unreliable, which transitions are fragile
- **Session intent**: what the next session should focus on

The practical implementation: a **`PROGRESS.md`** file in the project root, updated at the end of each session (either manually or via a command). Structured enough to be machine-readable, human-readable enough to be reviewed. Something like:

```markdown
# State Cartographer Progress

## Last updated: 2026-03-15, Session 7

## Graph status
- States discovered: 23
- States with anchors: 18
- States with deterministic transitions: 12
- States still vision-only: 11
- Wait states identified: 3

## Coverage
- Main menu tree: complete
- Dock/fleet management: complete
- Combat flow: partial (auto-battle mapped, manual combat not mapped)
- Event screens: not started (events rotate weekly, low priority)

## Open questions for human
- [ ] Is the "confirm retrofit" dialog the same state as "confirm enhance"?
- [ ] Should we treat the loading screen between menus as a state or ignore it?

## Known issues
- Anchor for "sortie select" screen breaks when event banner changes
- Back button from "ship detail" sometimes goes to dock, sometimes to formation

## Next session focus
- Add anchors to the 5 remaining dock substates
- Test locate() accuracy against the mock harness
- Investigate the back-button inconsistency
```

This file gets committed to the repo alongside the graph definition. It's the handoff document between sessions. Any agent starting a new session reads this first to understand where things stand.

Whether this lives as a rule ("always update PROGRESS.md before ending a session"), a command (`/cartographer:progress`), or a skill behavior is a design decision we can defer. The important thing is that the pattern exists and is documented.

---

## Summary of What Changed

| Topic | Previous state in docs | Revised position |
|---|---|---|
| Python/pytransitions | Recommended | Open question, spike needed |
| Multi-agent decomposition | Three defined agents | Aspirational; start with single skill, decompose later |
| Script interfaces | Specified with flags and JSON formats | Design after first real exploration, not before |
| Test fixtures | Detailed imagined scenarios | Generate from real captured data |
| Plugin structure | Full plugin from day one | Start flat, refactor into plugin when tools work |
| Observation gathering | Vision agent explores | Three paths: piggyback on existing automation, passive observation of human use, or active exploration |
| Mock harness timing | Mentioned but not sequenced | First priority after screenshot capture works |
| LLM runtime | Implicitly Claude Code | Multi-LLM; methodology is LLM-agnostic, scripts are universal |
| Cross-session continuity | Not addressed | PROGRESS.md pattern with structured handoff |
