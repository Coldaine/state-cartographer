# ALAS Live Ops Rules

These are the non-negotiable rules for live ALAS runs in this repo.

## Hard Rules

1. One controller only.
   - If more than one ALAS launcher is alive for the same config, the run is invalid.
   - `gui.py --run ...`, `run_patrickcustom.py`, and any other top-level launcher count as controllers.
   - Multiprocessing children are not controllers by themselves, but multiple top-level launchers are.

2. `Request human takeover` is terminal.
   - Treat it as a hard failure, not a soft warning.
   - Do not leave the emulator sitting there while a poller keeps tailing logs.

3. Black-screen warnings are low signal on their own.
   - They happen during transitions and provider churn.
   - The high-signal failure is black-screen churn plus `Wait too long` plus no recovery to a stable page.

4. A queued task list does not mean the agent is healthy.
   - If ALAS is stuck in `Restart` or login recovery, pending `Commission`, `Reward`, `Opsi*`, `Daily`, or `Hard`
     work is irrelevant until the controller stabilizes.

5. Passive polling is not enough.
   - Monitoring must detect duplicate controllers.
   - Monitoring must flag appended-log `Request human takeover` immediately.
   - Monitoring must record the last successful task and the last terminal recovery path.

## Current Repo Enforcement

- Screenshot capture is baked directly into `vendor/AzurLaneAutoScript/module/device/screenshot.py`.
  Every frame is written to `data/raw_stream/` when that directory exists. No wrapper script needed.
- No automated enforcement of duplicate-controller detection or takeover-exit is currently implemented
  (the runner that did this was deleted as over-engineering). Monitor ALAS logs manually.

## Practical Debug Sequence

1. Kill all ALAS launchers.
2. Confirm only one controller will be started.
3. Start the live run.
4. Watch for:
   - last successful task
   - page reached after login
   - whether `GOTO_MAIN` actually stabilizes the run
   - whether the run ends in `Request human takeover`
5. If takeover happens, stop treating the run as live progress.
