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

## Environment Setup

ALAS lives at `D:\_projects\ALAS_original` with its own uv-managed venv (Python 3.9.25).
It is separate from the MasterStateMachine repo and its Python 3.14 venv.

### Python and venv

```
Location:   D:\_projects\ALAS_original\.venv
Python:     3.9.25 (via uv — C:\Users\pmacl\AppData\Roaming\uv\python\cpython-3.9-windows-x86_64-none)
Created by: uv 0.10.7
```

ALAS requires Python 3.9.x. It will not run on Python 3.14 (or 3.11+) due to mxnet/cnocr
compatibility. The venv was created with `uv venv --python cpython-3.9`.

### Critical dependency pins

These packages must stay at specific versions. If the venv is rebuilt or deps are
upgraded, these are the ones that break:

| Package | Required | Why |
|---|---|---|
| `rich` | `==11.2.0` | ALAS pins this. 14.x uses a Windows console renderer that crashes on cp1252 with Unicode box-drawing characters |
| `numpy` | `==1.23.5` | mxnet 1.6.0 uses `np.bool` and `np.PZERO`, removed in numpy 1.24+ and 2.0+ respectively |
| `mxnet` | `==1.6.0` | Required by `cnocr==1.2.2`. Install with `--no-deps` to avoid pulling numpy 1.16 (won't build) |
| `cnocr` | `==1.2.2` | ALAS's OCR engine. Install with `--no-deps` for the same reason |
| `commonmark` | `==0.9.1` | Required by `rich==11.2.0` (newer rich uses `markdown-it-py` instead) |

### Rebuilding the venv from scratch

```bash
cd D:\_projects\ALAS_original
uv venv --python cpython-3.9
# Install most deps from requirements.txt
uv pip install --python .venv/Scripts/python.exe -r requirements.txt --no-deps
# Then fix the problem packages manually:
uv pip install --python .venv/Scripts/python.exe "rich==11.2.0" "commonmark==0.9.1"
uv pip install --python .venv/Scripts/python.exe "numpy==1.23.5"
uv pip install --python .venv/Scripts/python.exe "mxnet==1.6.0" --no-deps
uv pip install --python .venv/Scripts/python.exe "cnocr==1.2.2" --no-deps
```

Note: `--no-deps` on mxnet and cnocr is mandatory — their declared numpy pins (1.16.6)
cannot build on modern Windows. The pre-built wheels install fine; only the transitive
numpy build fails.

### Launch command

```bash
cd D:\_projects\ALAS_original
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe gui.py
```

`PYTHONIOENCODING=utf-8` is required. Without it, rich's log formatter crashes when
writing `│` and other box-drawing characters through the Windows cp1252 console codec.

**Web UI:** http://localhost:22267

### Killing stale processes

ALAS's `EnableReload` mechanism spawns child processes that can survive a parent crash.
Before restarting, check for orphans:

```powershell
# Find ALAS Python processes
Get-Process python* | Where-Object { $_.Path -like '*cpython-3.9*' } | Select-Object Id, Path
# Check what holds port 22267
Get-NetTCPConnection -LocalPort 22267 -ErrorAction SilentlyContinue
# Kill stale processes by PID
Stop-Process -Id <PID> -Force
```

## Current Repo Reality

- No automated enforcement of duplicate-controller detection or takeover-exit is currently implemented in the active repo surface.
- Do not assume older wrappers or runners still exist just because earlier docs mention them.
- Treat live ALAS operation here as manual/supervised unless and until that automation is re-earned.

## External ALAS Patches (applied directly in `D:\_projects\ALAS_original`)

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

## Log Files — Location and Format

ALAS writes two kinds of logs under `D:\_projects\ALAS_original\log\`:

| File pattern | What it contains |
|---|---|
| `{date}_gui.txt` | GUI process stdout — startup banner, webui launch, port conflicts |
| `{date}_{config_name}.txt` | Task execution log — navigation, OCR decisions, ADB calls, recovery |

The config name is whatever is selected in the UI or passed to `--run`. The helper wrapper in this repo is `vendor/launch_alas.ps1`; it launches the external ALAS checkout and defaults to the `alas` config unless you edit the script.

```
D:\_projects\ALAS_original\log\2026-03-25_alas.txt
```

### Tail the live log (PowerShell)

```powershell
$today = Get-Date -Format 'yyyy-MM-dd'
$log = "D:\_projects\ALAS_original\log\${today}_alas.txt"
Get-Content $log -Wait -Tail 50
```

If that file doesn't exist yet, ALAS hasn't executed a task — only the GUI started. Check `${today}_gui.txt` for the startup error.

### What a healthy task log looks like

```
│ 10:05:32.001 │ INFO │ Campaign │ 3-4
│ 10:05:32.415 │ INFO │ GOTO_MAIN │
│ 10:05:33.120 │ INFO │ Page main detected
│ 10:05:33.200 │ INFO │ Commission │ ...
│ 10:05:34.001 │ INFO │ Click │ START_COMMISSION (200, 350)
│ 10:05:36.823 │ INFO │ Screenshot │
```

Format: `│ {time} │ {level} │ {module} │ {message}`

### Warning patterns to watch for

| Pattern | Meaning |
|---|---|
| `Request human takeover` | **Hard failure — stop the run** |
| `Wait too long` + repeated black screen | Stuck, recovery is failing |
| Two `START` banners in `_gui.txt`, no task log | Startup crash before tasks ran |
| `[Errno 10048]` in `_gui.txt` | Port 22267 occupied by previous instance |

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
