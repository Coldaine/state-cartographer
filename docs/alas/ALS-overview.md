# ALS — ALAS Reference System

**Status: Running, actively used for observation harvesting (March 2026)**

ALAS (AzurLaneAutoScript) is a 9-year-old automation framework for Azur Lane. It is **not our runtime** — it is a reference implementation we learn from and a source of labeled observations.

## Role in State Cartographer

- **Observation source**: ALAS runs the game → monkeypatch captures every screenshot → corpus feeds VLM classification and anchor calibration
- **Ground truth for page names**: ALAS's internal page detection provides labels (but these are task-context labels, not visual labels — "page_reward" means the Reward task is running, not that a reward screen is visible)
- **Reference architecture**: ALAS solved every problem State Cartographer addresses — state detection, navigation, scheduling, error recovery — by hand for one game. We study its patterns.
- **NOT the live control plane**: State Cartographer's own harness will replace ALAS for live control

## What exists today

- `vendor/AzurLaneAutoScript/` — upstream LmeSzinc/AzurLaneAutoScript repo
- Monkeypatch in `vendor/.../module/device/screenshot.py:76-85` — saves every screenshot to `data/raw_stream/`
- `scripts/alas_observe_runner.py` — in-process monkeypatch of ALAS classes for full observation recording
- `scripts/alas_log_parser.py` — structured parser for ALAS log files (page events, actions, errors)
- `scripts/alas_converter.py` — converts ALAS button/page definitions to graph.json format
- `scripts/alas_action_inventory.py` — catalogs ALAS action patterns
- `scripts/alas_command_inventory.py` — catalogs ALAS module commands
- `scripts/alas_event_instrumentation.py` — event extraction from ALAS
- `scripts/alas_corpus_summarize.py` — corpus statistics

## Key findings (March 2026)

- **Black frames on restart**: atx-agent race condition. STOP hard-kills the process (no cleanup), START reconnects to a half-dead atx-agent. Recovery is reactive, not proactive.
- **ALAS labels are task-context, not visual**: "page_reward" means Reward task is active, screen may show Commission list. VLM labels are visually accurate. Don't use ALAS labels as visual ground truth.
- **Screenshot method**: uiautomator2 works. DroidCast produces excessive black frames on MEmu. DroidCast was the original cause of "bot does nothing" paralysis.
- **Meowfficer Fort**: consistently causes GameStuckError — the game screen goes to black frames during fort interaction, not a UI matching problem.

## Operational notes

- Config: `vendor/AzurLaneAutoScript/config/alas.json` (the active config, uses uiautomator2)
- Logs: `vendor/AzurLaneAutoScript/log/YYYY-MM-DD_alas.txt`
- Launch: via `gui.py`, select `alas` config in web UI at localhost:22267
- Clean slate before launch is mandatory — see CLAUDE.md for the PowerShell cleanup commands

## Key scripts

| Script | Lines | What it does |
|--------|-------|-------------|
| alas_observe_runner.py | ~450 | Monkeypatch ALAS for full observation recording |
| alas_log_parser.py | ~1100 | Structured parser for ALAS log files |
| alas_converter.py | ~350 | Convert ALAS definitions to graph.json |
