# ALAS Observation Launch Plan

## What we want

Two distinct goals:

1. **Behavior analysis** — understand what tasks ALAS runs, which fail, and why.
   Requires: ALAS running + log file readable. No screenshots needed.

2. **Labeled screenshot corpus** — labeled corpus for anchor calibration.
   Requires: ALAS running + sidecar capturing screenshots + log-join + dedup.

Both share the same launch procedure. The sidecar is additive.

---

## Why Claude cannot launch ALAS

The launch script (`vendor/launch_alas.ps1`) is PowerShell. Claude's bash tool
cannot set `$env:PYTHONIOENCODING` or run `Set-Location`. Piping the output
through `head -N` kills the process after N lines. Background launch via bash
has no way to cleanly attach to the console process tree.

**Conclusion:** The user must run the launch script in their own terminal. Claude
reads the output (log file) after the fact or in parallel.

---

## Step 1 — Launch ALAS (user runs this)

Open a terminal and run:

```powershell
pwsh vendor/launch_alas.ps1
```

The script handles:
- Kill all ALAS/Python processes matching `gui.py|AzurLane`
- Free port 22267
- Wait 3 seconds
- Set `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`
- `cd vendor/AzurLaneAutoScript`
- Launch `.venv\Scripts\python.exe gui.py --run PatrickCustom`

Leave this terminal open. ALAS writes its log to:
```
vendor/AzurLaneAutoScript/log/YYYY-MM-DD_PatrickCustom.txt
```

Normal startup takes 15–30 seconds (Unity loading = black frames, not an error).

---

## Step 2a — Behavior analysis (log only)

Once ALAS has been running for a few minutes, Claude reads the log:

```bash
uv run python scripts/alas_log_parser.py \
  --file vendor/AzurLaneAutoScript/log/$(date +%Y-%m-%d)_PatrickCustom.txt \
  --summary --timeline --errors
```

This produces:
- Task execution timeline (start/end/duration/success)
- Error and exception summary
- ADB/device issues

**Known bug in alas_log_parser.py:** `find_latest_log()` at line 944 globs
`*_alas.txt` — this pattern never matches `2026-03-19_PatrickCustom.txt`.
The `--latest` flag is broken. Use explicit `--file` path instead.

---

## Step 2b — Observation pipeline (sidecar)

This is the timestamp-join approach from memory: screenshots are captured and
labeled by the current ALAS log state at capture time.

### What to build: `scripts/alas_sidecar.py`

```
ALAS (terminal 1)                    Sidecar (terminal 2)
  └─ logs page switches              └─ tails log file
  └─ logs task start/end             └─ tracks current page + task
  └─ takes screenshots (internal)    └─ captures screenshots via ADB
                                     └─ writes labeled JSONL index
```

**Sidecar responsibilities:**
1. Open the ALAS log file (or wait for it to appear)
2. Tail it in real-time (read new lines as they arrive, sleep poll)
3. Feed new lines to `NavigationAnalyzer` and `TaskAnalyzer` to track:
   - `current_page` — from "Page switch: X -> Y" log entries
   - `current_task` — from "Scheduler: Start task `X`" entries
4. Every N seconds (configurable, default 2s), call `adb_bridge.screenshot()`
5. Write to a JSONL index: one record per capture:
   ```json
   {"ts": "2026-03-19T14:23:01.452Z", "path": "data/sidecar/000123.png",
    "alas_page": "page_main", "alas_task": "Commission", "log_line": 4821}
   ```
6. On CTRL+C: print summary (N captures, M unique pages seen)

**Then post-run:**
```bash
# Dedup the corpus per page label
uv run python scripts/screenshot_dedupe.py \
  --input data/sidecar/ \
  --output data/sidecar/dedup_report.json

# Inspect the labeled index
cat data/sidecar/index.jsonl | python -c "
import sys, json, collections
recs = [json.loads(l) for l in sys.stdin]
pages = collections.Counter(r['alas_page'] for r in recs)
print(f'Total: {len(recs)} captures, {len(pages)} unique pages')
for p, n in pages.most_common(): print(f'  {p}: {n}')
"
```

### Sidecar launch (terminal 2, after ALAS is running)

```bash
uv run python scripts/alas_sidecar.py \
  --log vendor/AzurLaneAutoScript/log/$(date +%Y-%m-%d)_PatrickCustom.txt \
  --serial 127.0.0.1:21513 \
  --interval 2 \
  --out data/sidecar
```

---

## What NOT to do

| Approach | Why not |
|---|---|
| `alas_observe_runner.py` monkeypatch | Runs headless (no GUI), calls uncalibrated `locate.py` (all return "unknown"), adds complexity with no benefit until anchors are calibrated |
| `locate.py` for labeling | Uncalibrated — returns "unknown" for everything, per prior session |
| Claude launching ALAS via bash | PowerShell env vars fail, piping kills the process |
| Running ALAS in background from bash | Process tree is wrong, stdout/stderr unmanaged |

---

## What Claude/subagents do after launch

Once ALAS is running and the log file exists:

1. **Log tail agent** — reads `YYYY-MM-DD_PatrickCustom.txt`, runs
   `alas_log_parser.py`, reports task timeline + errors
2. **Config reader** — reads `vendor/AzurLaneAutoScript/config/PatrickCustom.json`
   to enumerate which tasks are enabled (no ALAS needed for this)
3. **Sidecar runner** (if corpus needed) — user starts sidecar in terminal 2,
   Claude checks `data/sidecar/index.jsonl` progress after N minutes

---

## Existing bugs to fix before next run

1. **`alas_log_parser.py:944`** — `find_latest_log()` globs `*_alas.txt`, never
   matches `YYYY-MM-DD_PatrickCustom.txt`. Fix: glob `*.txt` sorted by mtime,
   or accept a config-name argument.

2. **`alas_sidecar.py` does not exist yet** — needs to be written (see above spec).
