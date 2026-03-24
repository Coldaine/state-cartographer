# North Star

> Historical note: moved from `docs/NORTH_STAR.md` during the 2026 documentation realignment.

This document describes the desired end state of the project.

It is strategic target material, not a statement of current capability.

For current truth and near-term movement, read:
- [current-reality.md](/mnt/d/_projects/MasterStateMachine/docs/project/current-reality.md)
- [current-plan.md](/mnt/d/_projects/MasterStateMachine/docs/plans/current-plan.md)

## Desired End State

State Cartographer automates Azur Lane daily operations with a supervised runtime that is reliable, inspectable, and incrementally improvable.

## Goals

1. **Automate daily tasks**
   - commissions, research, dorm, meowfficer, guild, dailies, exercise, shop, shipyard, OpSi
   - the mature system can run the daily loop without routine human intervention

2. **Navigation is cheap and deterministic where earned**
   - known routes should execute as trusted action sequences rather than repeated high-cost model calls

3. **State detection is reliable**
   - the system should maintain trustworthy orientation across rendering glitches, black frames, and UI variation

4. **Recovery is automatic for known failures**
   - known popups, loading states, crashes, and stuck patterns should have known recovery paths

5. **Progressive determinism**
   - interactions may start vision-heavy but should become cheaper and more deterministic as the project learns them

6. **Resource awareness gates execution**
   - task execution should be constrained by observed game state, not by guessed or stale bookkeeping

7. **Data collection is a first-class capability**
   - the system should be able to inventory, snapshot, and revisit rich game state, not just click through daily chores

8. **Gestures are first-class actions**
   - swipes, pans, and other non-tap interactions should be represented and replayed intentionally

9. **Recording is rich enough for replay and diagnosis**
   - screenshots, actions, transitions, and failures should be recoverable enough to support analysis and repair

10. **Autonomy is paired with escalation**
   - routine work should not require supervision, but genuine ambiguity should escalate with context

11. **Escalation is decision-ready**
   - escalation should include enough state and recent-history context that a supervisor can act without re-investigating from scratch

12. **The system is buildable incrementally**
   - parts of the stack should add value before the full system exists

13. **Decision support remains explicit**
   - simple threshold rules can be automated; higher-judgment choices should surface structured context to a supervisor
