# Azur Lane Automation: Execution Plan

This document describes the build sequence. Each phase produces a working capability that can be validated before moving to the next. You cannot skip phases; each one depends on the previous.

## Phase 1: Single-Model Perception-Action Loop

**Goal**: A VLM can see a game screenshot and reliably identify what screen it's looking at, and the system can dispatch a single action and confirm it worked.

**What to build**:

- Connect to an Android emulator and capture screenshots programmatically
- Send a screenshot to a locally-hosted GUI-specialized VLM
- Get back structured output: what screen is this, what are the interactable elements
- Issue a single action (tap a specific element) through an automation harness
- Capture a follow-up screenshot and confirm the screen changed

**Validation gate**: Given a screenshot of the main menu, the system correctly identifies it, taps a known button, and confirms it arrived at the expected next screen. This must work 10 times in a row without failure.

**What this does NOT include**: multiple actions in sequence, error handling, escalation, logging infrastructure. Just one action, verified.

## Phase 2: Sequential Navigation with Logging

**Goal**: The system can execute a multi-step navigation sequence (e.g., main menu to a specific sub-menu and back) while logging every step.

**What to build**:

- Chain multiple perception-action cycles together
- Implement the logging format: screenshot pairs, screen identification, action taken, outcome
- Handle basic timing: wait for screen transitions before acting, detect loading screens
- Handle the "nothing changed" case: retry the action or flag it

**Validation gate**: The system navigates a known 5+ step path through the game's menus, logging every step, and the log is a complete, replayable record of what happened. Run it 10 times; it should succeed at least 8 times without human intervention.

**What this does NOT include**: handling unknown screens, escalation, multiple model tiers. One model, known paths only.

## Phase 3: Feedback Confirmation and Error Recovery

**Goal**: The system detects when things go wrong and can recover from common failure modes.

**What to build**:

- After each action, confirm the screen matches one of the expected next states
- If it doesn't match: retry the action (once), then flag the state as unexpected
- Handle common failure modes: unexpected popups/dialogs (identify and dismiss), game connection errors (detect reconnection flow and wait), animation/loading delays (wait and retry)

**Validation gate**: Intentionally inject failure conditions (trigger a popup mid-navigation, simulate a slow load) and verify the system recovers without human intervention. It should handle at least 3 distinct failure types.

**What this does NOT include**: escalation to a different model. Recovery at this phase uses the same model; it just retries or waits.

## Phase 4: Escalation (Second Model Tier)

**Goal**: When the primary model can't handle a screen, the system automatically escalates to a more capable model and resolves the situation.

**What to build**:

- Define the escalation trigger: low confidence score, unrecognized screen, repeated failure after retry
- Stand up a second model tier (larger VLM, or same model with reasoning/chain-of-thought mode)
- Pass context to the higher tier: current screenshot, recent action history, the lower tier's interpretation
- Higher tier resolves the situation and returns control to the lower tier

**Validation gate**: Navigate a known path but include one screen the Executor has never seen. Verify it escalates, the Analyst resolves it, and the system continues the path. The escalation should appear in the log with full context.

## Phase 5: Teacher Demonstration and Logging

**Goal**: A frontier-class model can execute a full task (not just navigation, but a complete gameplay task like collecting daily rewards) while producing a log detailed enough to distill from.

**What to build**:

- Connect a frontier model (via API) as the Teacher tier
- Give it a task description and let it execute, logging every action with full provenance
- The Teacher's log must capture: every screenshot, every decision rationale, every action with parameters, every screen transition
- Human review interface: you can watch the log and say "yes, this is correct" or "no, it did this wrong"

**Validation gate**: The Teacher completes one full daily task (e.g., collecting mail, or running a commission cycle) and the log is clean enough that a human reviewing it can identify every screen and action without ambiguity.

## Phase 6: Distillation

**Goal**: A Teacher demonstration can be converted into Executor-tier patterns so future runs of that task are fast.

**What to build**:

- A process that takes a Teacher demonstration log and produces: screen recognition templates (images or OCR targets), action definitions, transition expectations (next-screen graph)
- These patterns are encoded in the format the Executor consumes (pipeline nodes, template images, etc.)
- The Executor can now run the distilled task without Teacher involvement
- The distilled task runs significantly faster than the Teacher demonstration

**Validation gate**: Distill a Teacher demonstration into Executor patterns. Run the same task with the Executor using the distilled patterns. It should complete the task successfully at a fraction of the Teacher's execution time. The speed improvement should be at least 5x.

## Phase 7: Strategic Layer (Future)

**Goal**: A planning layer that decides *what* tasks to run, in what order, and when. This is the consumer of the substrate built in Phases 1-6.

This phase is intentionally underspecified. It depends entirely on the substrate being solid. Only begin this after Phases 1-6 are validated.

At this point, all you need to do is tell the strategic layer what the tasks are. The substrate handles everything else.
