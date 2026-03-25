# Technical Hypothesis: The Stability Trap

> Historical note: moved from `docs/research/RES-stability-trap-analysis.md` during the 2026 documentation realignment.

## Status

This document records a durable failure hypothesis from ALAS-era live investigation.

It is a hypothesis supported by observed evidence. It is not a closed proof.

See also:
- [ALS-live-ops.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-live-ops.md)
- [backend-lessons.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/backend-lessons.md)
- [todo.md](/mnt/d/_projects/MasterStateMachine/docs/todo.md)

## Problem Statement

A recurring failure mode was: the bot appeared to do nothing for long periods, then eventually hit `GameStuckError` and restarted, even though occasional valid frames were still visible.

## Main Hypothesis

The most plausible explanation was an interaction between:

- unstable screenshot capture
- ALAS-style consecutive-frame stability checks
- a requirement for multiple consecutive successful detections before acting

If valid frames arrive too sparsely, the controller repeatedly loses its detection streak and never takes the transition it is waiting for.

## Observed Evidence

The evidence that motivated this hypothesis was:

- intermittent valid frames mixed with many black or partial frames
- repeated long waits on screens that visually appeared correct
- recovery/restart behavior after prolonged inactivity
- logs and raw-frame captures consistent with sparse valid-frame windows

## What This Suggests

If the upstream controller requires several consecutive confirmations before acting, a noisy provider can create a false "stability" requirement that is statistically hard to satisfy.

The practical result is paralysis:
- the screen is sometimes visible
- the target may really be present
- but the controller almost never reaches its action threshold

## Mitigation Direction

The mitigation direction suggested by this hypothesis is:

- reduce dependence on long consecutive-success streaks where appropriate
- improve screenshot/provider stability first
- distinguish provider instability from true UI ambiguity
- prefer measurement over intuition when evaluating wait logic

## What Is Not Yet Proven

These alternatives were not fully ruled out:

- control commands were sent but not processed by the emulator
- invisible overlays or wait states were blocking action
- a different provider/control-path bug was the primary cause

## Practical Use

Use this document as preserved failure analysis.

Do not treat the numeric estimates from the original investigation as current truth unless they are re-measured on the current stack.
