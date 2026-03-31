# Tap Chain Design Notes

## Context

During live battle testing (2026-03-28), we realized the current Pilot harness is too chatty with screenshots. When navigating Azur Lane's deterministic UI flows, we were:

1. Tap enemy on map
2. Screenshot to see what happened  
3. See Formation screen
4. Tap Battle
5. Screenshot to see what happened
6. ...

This is wasteful. Azur Lane has **predictable state transitions**:
- `battle_map` → tap enemy → `formation_screen` → tap Battle → `combat_active`

## Proposal: Tap Chain

A `tap_chain()` method that executes a sequence of taps with delays, capturing screenshots only at key verification points (or optionally, capturing all for corpus building).

## Why Now?

Even though we're building toward a full state machine, we need basic "fire and forget" sequences for:
- Rapid prototyping of battle flows
- Building the screenshot corpus for later VLM training
- Manual override during testing

## Why Tentative

This is **not the final architecture**. We don't know yet:
- If delays should be fixed or adaptive
- If we need conditional branches (tap X if region Y matches)
- If timing varies by device/emulator load
- If we need rollback on fault

The tap chain is a **scaffolding tool** — useful now, likely replaced by the proper state machine later.

## Future: Mini State Machine

The end goal is a state machine where each node knows:
- Expected screen signature (VLM embedding or template match)
- Available actions with preconditions
- Timeout handling and recovery paths

Tap chain is the poor man's version of that.

---
*Written during live Azur Lane combat testing, 2026-03-28*
