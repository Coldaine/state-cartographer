# Azur Lane Automation: Architecture

## Tiered Model Architecture

The system uses a spectrum of vision-language models, not a single model. The tiers are defined by *role*, not by specific model. Model assignment to roles is a tuning parameter that changes over time.

### Executor

Sees the screen, picks the next action, dispatches it. Must be fast; sub-second to low single-digit seconds per cycle. Handles the common case: known screens, known transitions, well-understood patterns.

The Executor's end state for fully-learned patterns is not VLM inference at all. It's deterministic recognition (template matching, OCR) with visual verification checkpoints. The VLM is a starting point because it handles novel screens; deterministic methods are where distillation takes you. Even deterministic sequences use visual confirmation at each step; the system is never blind.

### Analyst

Handles ambiguity. When the Executor encounters an unknown screen, a popup it hasn't seen, or a state it can't confidently classify, it escalates to the Analyst. Seconds of latency are acceptable here because this is the uncommon path.

The Analyst is a more capable vision-language model, or the same model with a reasoning/chain-of-thought mode enabled. It receives the screenshot, recent action history, and the Executor's failed interpretation, and resolves the situation.

### Teacher

Demonstrates new tasks. When you want to automate something the system has never done, the Teacher runs through it with full logging, maximum accuracy, and no speed constraint. Minutes per action are fine. The Teacher's output is not automation; it's a demonstration log that the distillation process converts into Executor-tier patterns.

The Teacher may be a frontier-class model accessed via API. It's too slow and expensive for the Executor loop, but it only runs when teaching new tasks.

## The Perception-Action-Feedback Loop

The core loop that runs on every action cycle:

1. **Capture**: take a screenshot from the emulator
2. **Perceive**: send to the active-tier model; receive structured output (screen identification, visible UI elements, recommended action)
3. **Act**: dispatch the action to the automation harness
4. **Confirm**: capture a new screenshot; verify the expected state was reached
5. **Route**: if confirmation succeeds, loop back to Capture. If it fails, escalate.

The loop must handle:

- Loading screens and transitions (wait and retry; do not act during animations)
- Unexpected dialogs or popups (identify and dismiss, or escalate)
- Network errors within the game (detect and handle reconnection flows)
- Stuck states (same screen after acting; escalate after N retries)

## Escalation Protocol

Escalation is automatic. The human is not in the escalation loop during normal operation.

1. The active tier signals low confidence, or the feedback step detects an unexpected state
2. The system escalates to the next tier up
3. The higher tier receives: the current screenshot, recent action history, and the lower tier's interpretation
4. The higher tier resolves the situation and returns control downward

Escalation should be logged. Frequent escalation on the same screen is a signal that the Executor needs retraining or the state machine needs a new node.

## Action Interface

The decision engine works with a high-level action vocabulary, never with raw input commands. The adapter layer translates high-level actions into harness-specific calls. This abstraction allows swapping automation harnesses without changing the decision logic.

The action vocabulary covers at minimum: tap a target, swipe in a direction, wait for a condition, navigate back, confirm/dismiss a dialog. The exact set is defined by the harness adapter.

## Logging and Provenance

Every action cycle produces a log record:

- Timestamp
- Screenshot (before and after)
- Which tier handled the decision
- Screen state interpretation
- Action selected and parameters
- Expected outcome vs. actual outcome
- Confidence score (if available)

Logging serves two purposes: debugging (replay the exact sequence when something goes wrong) and distillation (the Teacher's logged demonstrations become training data for lower tiers).

## Distillation Lifecycle

This is how the system gets faster over time.

1. The Teacher demonstrates a new task with full logging
2. The demonstration log is reviewed (human gate during bootstrap; automated gate later)
3. The demonstration is encoded into a pattern the Executor can run: screen recognition templates, action definitions, transition expectations
4. Future runs of that task execute at Executor speed

The natural encoding target is a declarative pipeline: a directed graph of screen states, where each node specifies how to recognize "I'm on this screen," what action to take, and which screens might come next. This maps well onto existing automation framework patterns (e.g., JSON-defined pipelines with recognition methods and next-chains).

The distillation output for a given node might be:

- A template image for fast matching (cheapest)
- An OCR target string (cheap)
- A small VLM prompt for screens that resist template matching (moderate)
- A full VLM call for screens that are genuinely variable (most expensive; signals incomplete distillation)

Over time, the proportion of nodes using template matching should grow and the proportion using VLM calls should shrink. That's the optimization axis.

## State Representation

Screens are identified as nodes in a directed graph. Each node has:

- A name (human-readable identifier for the screen)
- One or more recognition methods (ordered cheapest to most expensive)
- Available actions from that screen
- Expected transitions (action X from this screen leads to screen Y)

The graph starts empty and grows as the Teacher demonstrates tasks and distillation encodes new nodes. The graph is the system's knowledge of the game's UI.
