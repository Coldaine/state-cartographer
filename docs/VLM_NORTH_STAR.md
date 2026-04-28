# Azur Lane Automation: North Star

## The Problem

Azur Lane has dozens of recurring tasks (dailies, weeklies, commissions, event farming, resource collection) that must be executed through a slow, menu-driven UI. Each task involves navigating between screens, tapping buttons, waiting for transitions, and repeating. A human can do this but it's tedious and time-consuming. We want a system that does it autonomously.

## The Core Constraint

**Throughput.** A session involves hundreds to thousands of individual actions (tap, swipe, wait, confirm). If each action requires a slow inference call, the session takes longer than doing it by hand. The system must execute actions fast enough that automated sessions complete in a timeframe comparable to manual play.

This is not a cost constraint. It's not a quality constraint. It's a speed constraint. The architecture must be shaped around this.

## What "Done" Looks Like

1. You tell the system what tasks to perform.
2. It performs them autonomously, at reasonable speed, without babysitting.
3. When it encounters something new, it escalates to a smarter (slower) model, resolves the situation, and keeps going.
4. Over time, it gets faster: patterns that once required an expensive model get distilled into cheap, fast recognition.
5. When you want to teach it a new task, you run a demonstration pass with a powerful model, review the result, and the system encodes it for fast future execution.

## System Boundary

### This System Is

The middle layer: perception, decision, action dispatch, and feedback confirmation. It sees the screen, decides what to do, tells something else to do it, and verifies it worked.

### This System Is Not

**Below it**: input injection, emulator management, device automation. These are solved problems. The system consumes an automation harness through an adapter; it does not own the harness.

**Above it**: task definition, prioritization, scheduling, session orchestration. The strategic layer that decides *what* to automate is a future consumer of this substrate. We build the substrate first; the strategy layer has nothing to plug into without it.

## Constraints

### Game Characteristics

- Slow-paced, menu-driven navigation; not real-time combat
- Deterministic screen flows: given a screen and an action, the next screen is predictable
- Large but finite set of screens and UI states
- Recurring task structure with dozens of distinct task types
- Occasional event content introducing new screens and flows

### Speed Over Everything Else

- The system must be fast on the common path (known screens, known actions)
- It is acceptable to be slow on the uncommon path (novel screens, ambiguous states)
- The system must get faster over time as more patterns are learned
