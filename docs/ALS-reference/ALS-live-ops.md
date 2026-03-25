# ALAS Live Ops Rules

> Historical note: moved from `docs/alas/ALS-live-ops.md` during the 2026 documentation realignment.

These are the non-negotiable rules for live ALAS runs in this repo.

See also:
- [ALS-overview.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-overview.md)
- [backend-lessons.md](/mnt/d/_projects/MasterStateMachine/docs/runtime/backend-lessons.md)

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

## Current Repo Reality

- No automated enforcement of duplicate-controller detection or takeover-exit is currently implemented in the active repo surface.
- Do not assume older wrappers or runners still exist just because earlier docs mention them.
- Treat live ALAS operation here as manual/supervised unless and until that automation is re-earned.

## Vendor Patches (applied directly in `vendor/AzurLaneAutoScript/`)

These are unstaged local edits — not committed into the submodule. They survive normal use but are
wiped by `git submodule update --force` or `git checkout .` inside the vendor dir. Re-apply manually
if needed. There are **three patched files**, all intentional:

### 1. `module/device/screenshot.py` — corpus capture shim

The only patch needed for observation corpus collection. Two changes:
- **Retry loop**: `for _ in range(2)` → `for _ in range(10)` — more retries before giving up on black
  frames (OpenGL intermittently returns blank on the first pull).
- **Frame save block** (inserted after the existing `screenshot_deque.append`):
  ```python
  _raw_stream = os.path.join(os.path.dirname(...), '..', '..', 'data', 'raw_stream')
  if os.path.isdir(_raw_stream):
      ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
      cv2.imwrite(os.path.join(_raw_stream, f'{ts}.png'), self.image)
  ```
  Saves every frame to `data/raw_stream/` only when that directory exists — zero overhead when it
  doesn't. No wrapper script needed; this is the entire observation pipeline entry point.
- **`time.sleep(0.1)`** added before `continue` in the retry loop — brief pause between blank-frame
  retries.

### 2. `module/device/device.py` — extended stuck timer

```python
stuck_timer_long = Timer(900, count=900)  # was Timer(180, count=180)
```

Extends the "stuck too long" timeout from 3 minutes to 15 minutes. Required for OpsiStronghold and
other long battle sequences where ALAS would otherwise declare the device stuck mid-combat.

### 3. `module/tactical/tactical_class.py` — tactical class start resilience

Adds a `not_start_count` counter so that `TACTICAL_CLASS_START` must be absent for **2 consecutive
checks** before the function returns `False`. Prevents a single missed frame from aborting tactical
class enrollment.

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
