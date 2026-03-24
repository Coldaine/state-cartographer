# EXE — PilotBridge Rework Plan

> Status: PLANNED — not yet executed.
> Entry point for understanding the cleanup scope and rationale.

## What PilotBridge Is

`scripts/pilot_bridge.py` is the **only working live screenshot/action backend**
for MEmu/Azur Lane. Its three real responsibilities are:

1. **Screenshot via DroidCast restart cycle** — Kill existing `droidcast_raw` on
   the device, start a fresh instance via the ATX agent HTTP API, wait for port
   53516, `GET /preview`, decode JPEG → PIL Image. Takes ~3 seconds per call.
   This is the only method that works on MEmu with DirectX rendering (normal
   Android screencap returns blank because the GPU bypasses the compositor).

2. **ADB tap/swipe** — `adb shell input tap x y` and `adb shell input swipe ...`
   via subprocess. Straightforward.

3. **NDJSON event recording** — Every action appended to
   `data/events/{run_id}.ndjson` via `execution_event_log.py`.

Everything else in the current 575-line file is either dead code on MEmu, ALAS
coexistence logic, game-specific popup handling that doesn't belong here, or
over-engineered port management for a single-device setup.

---

## What to Remove / Simplify

### 1. ATX fast-path screenshot (dead code on MEmu)

`screenshot_via_atx()` calls `GET /screenshot` on the ATX agent. On MEmu with
DirectX rendering this **always** returns a blank frame. The current code:

1. Tries `screenshot_via_atx()`
2. Checks if blank with `_is_blank_frame()`
3. Falls back to `_restart_and_capture()`

Step 1-2 add ~100ms of overhead and two code paths to every screenshot. The
blank-frame check exists only because of this blind attempt. For MEmu the
correct behavior is: **always go directly to `_restart_and_capture()`**.

**Action**: Remove `screenshot_via_atx()`, `_is_blank_frame()`, and the
try/fallback logic in `screenshot()`. Set a class constant
`SCREENSHOT_METHOD = "droidcast"` for future extensibility if needed.

### 2. `handle_startup_popups()` — game logic in the wrong layer

This method encodes Azur Lane startup popup coordinates directly in
`PilotBridge`. The bridge is supposed to be a generic action executor for the
emulator, not a game AI. Popup handling belongs in:
- A startup entry in `examples/azur-lane/tasks.json` as a task step sequence, or
- A startup recovery routine in `executor.py`

**Action**: Move the `STARTUP_POPUP_TAP_SEQUENCE` constant and
`handle_startup_popups()` to a `scripts/startup.py` utility or inline the
logic in `executor.py`'s preflight. Remove from `PilotBridge`.

### 3. `_ensure_forward()` — over-engineered for a single device

The cross-device ownership check (`if owner_serial != self.serial`) handles a
scenario where multiple physical devices share local forward ports. This repo
has exactly one MEmu instance (`127.0.0.1:21513`). The ALAS coexistence guard
(don't overwrite ALAS's existing DroidCast forward if running on port 22267)
is real and should be kept, but it can be done in 5 lines.

**Action**: Simplify `_ensure_forward()` to: check if the forward already
exists for our serial with the right target, if yes return, if no set it. The
ALAS coexistence check for `replace_existing` stays because it prevents
disrupting a running ALAS session.

### 4. `threading.RLock` — probably not needed

`PilotBridge` is used by a single `executor.py` instance in a single thread.
The lock adds overhead and complexity with no benefit unless we add a concurrent
caller (not planned). The lock can be dropped from `__init__`, `connect()`,
`screenshot()`, `tap()`, and `swipe()`.

**Action**: Remove `self._lock` and all `with self._lock:` blocks. Document
that the class is not thread-safe and callers are responsible for serialization
if needed.

---

## What to Keep (Exactly as Is)

- `_adb()` helper function — clean, correct, reusable
- `_decode_bytes()` helper
- `connect()` flow — ADB connect + push APK + forward ports + verify ATX +
  test capture. This is the right sequence.
- `_alas_running()` — socket probe on port 22267. Used in `_restart_and_capture()`
  to share ALAS's DroidCast instead of killing it.
- `_restart_and_capture()` — the core DroidCast restart cycle. Keep exactly as
  is, including the ALAS coexistence branch.
- `_capture_preview()` — HTTP fetch + cv2 decode.
- `tap()`, `swipe()`, `back()`, `wait()` — keep as is.
- `log_observation()` — keep as is.
- CLI `main()` — keep as is (connect / screenshot / tap subcommands).

---

## Resulting Size Estimate

Current: ~575 lines
After rework: ~350 lines (~200 lines removed)

The class surface stays stable — `connect()`, `screenshot()`, `tap()`,
`swipe()`, `back()`, `wait()`, `log_observation()` all remain. No breaking
changes to callers (`executor.py`, tests).

---

## Test Impact

`tests/test_pilot_bridge.py` mocks ADB and HTTP responses. The ATX screenshot
path tests (`test_screenshot_via_atx*`, `test_blank_frame_fallback`) will be
deleted. Everything else stays. The `handle_startup_popups` tests move to
wherever that logic lands (executor or startup.py).

---

## Implementation Order

1. Remove `screenshot_via_atx()` + `_is_blank_frame()` + try/fallback in `screenshot()`
2. Remove `threading.RLock` + all lock blocks
3. Move `handle_startup_popups()` + `STARTUP_POPUP_TAP_SEQUENCE` out
4. Simplify `_ensure_forward()` — keep ALAS coexistence, remove cross-device logic
5. Update tests accordingly
6. Run full test suite: `uv run pytest tests/ -v`
