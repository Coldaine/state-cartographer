# North Star

State Cartographer automates Azur Lane daily operations. These are the goals for the finished system.

## Goals

1. **Automate daily tasks** — commissions, research, dorm, meowfficer, guild, dailies, exercise, shop, shipyard, OpSi. The system runs the full daily loop without human involvement.

2. **Navigation is cheap and deterministic** — given the state graph, move between any two screens without vision reasoning. Known routes execute as tap sequences, not LLM calls.

3. **State detection is reliable** — the system always knows what screen it's on. Rendering glitches, black frames, and UI variations don't cause it to lose track.

4. **Recovery is automatic for known errors** — unexpected popups, loading screens, black frame floods, app crashes, and stuck states are handled without escalation. Known failure patterns have known recovery paths.

5. **Progressive determinism** — interactions that start as vision-driven become deterministic after enough observations. The system gets cheaper and faster over time. The goal is to shrink the vision-required set to <5% of all operations.

6. **Resource awareness gates execution** — the system checks resource requirements before running tasks. Don't farm if oil < 200. Resources are observed from the game UI, not computed.

7. **Data collection is a first-class operation** — the system can inventory the entire dock (400+ ships), read ship stats/equipment/skills, record fleet formations, snapshot resource levels. Pagination is robust, interruptible, and resumable from checkpoints.

8. **Gestures are first-class actions** — swipes through the dock, map panning in OpSi, pinch-to-zoom. Gestures are recorded as parameterized actions (start, end, duration) and replayable.

9. **Recording captures everything** — every screenshot, tap, state transition, and error is logged in an append-only event log. The corpus enables replay, debugging, calibration, and learning.

10. **The system runs autonomously and escalates genuine decisions** — routine operations don't require a supervisor. Escalation happens with full context: screenshot, current state candidates, recent actions, what was tried, proposed recovery options.

11. **Escalation is rich, not blind** — when the system escalates, it provides enough context for the supervisor (human or AI) to make a decision without re-investigating from scratch.

12. **The system is buildable incrementally** — each layer works independently and adds value on its own. Navigation works without scheduling. Scheduling works without data collection. But the full stack is where the real power lives.

13. **Decision support** — simple decisions (threshold gating) are automatic. Complex decisions (which of 4 commissions to accept based on rewards vs duration) are escalated with structured context so the supervisor brings judgment and the tooling brings speed.
