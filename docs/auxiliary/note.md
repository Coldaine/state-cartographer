# Bot Monitor Note

## First loop completed: 2026-03-30 20:43 CDT

### How to start the bot
- **Web UI**: http://localhost:22267 — click the start button. Web UI tracks the process.
- **CLI fallback**: `.venv/Scripts/python alas.py` from the repo root. Runs the scheduler loop directly. Web UI won't track it but the bot works fine. Log goes to `./log/YYYY-MM-DD_alas.txt`.
- **No REST API** exists to start/stop programmatically.

### Current approach
Starting via CLI with `run_in_background` so we can monitor the log. The web UI (port 22267) is still running separately.

### Changes in working tree
- `alas.py` — crash recovery + bump + debug counter
- `module/device/screenshot.py` — debug screenshot saving (pre-existing)
- `module/webui/process_manager.py` — reduced log buffer for UI perf
- `parse_logs.py` — log analysis tool (untracked)
