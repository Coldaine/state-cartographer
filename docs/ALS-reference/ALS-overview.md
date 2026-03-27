# ALS — ALAS: The Original Automation

> Historical note: moved from `docs/alas/ALS-overview.md` during the 2026 documentation realignment.

**Status: Active operational automation — runs daily until State Cartographer's runtime supersedes it**

ALAS (AzurLaneAutoScript) is the original automation framework for Azur Lane. It is a mature, working system that already handles daily tasks, navigation, scheduling, and recovery. **This repo is building its replacement.**

Until State Cartographer ships a working runtime, ALAS is the only automation running. It is not a passive reference — it is the live system that performs the daily loop on the local MEmu emulator.

See also:
- [ALS-live-ops.md](/mnt/d/_projects/MasterStateMachine/docs/ALS-reference/ALS-live-ops.md) — operational rules for running ALAS

## What ALAS Is

ALAS is a Python automation framework that:
- Uses **template matching** (OpenCV) for screen state detection
- Has a full **page/navigation graph** with deterministic goto logic
- Runs a **task scheduler** that cycles through dailies, commissions, research, OpSi, etc.
- Handles **recovery**: popups, loading screens, crashes, stuck detection
- Controls the emulator via **ADB** (screenshots, taps, swipes)
- Exposes a **web UI** (pywebio + uvicorn) for configuration and monitoring

It has years of operational maturity. It works. The question is not whether ALAS can automate the game — it already does. The question is whether a VLM-driven replacement can do it better: more inspectable, more adaptable, with progressive determinism and structured escalation.

## Why We're Replacing It

ALAS works, but it has fundamental limitations this project aims to overcome:
- **Template matching is brittle** — asset updates, resolution changes, and UI variations require manual template maintenance
- **No visual understanding** — ALAS matches pixels, it doesn't comprehend what's on screen
- **Opaque failure modes** — when ALAS fails, diagnosis requires reading code, not structured context
- **No progressive learning** — every interaction costs the same whether it's the first time or the thousandth
- **Escalation is binary** — either it works or "Request human takeover" with minimal context

State Cartographer aims to replace these with VLM-driven state detection, structured event logging, progressive determinism, and decision-ready escalation.

## Role in This Repo

ALAS serves three roles simultaneously:

1. **Active operational system** — it runs the daily automation right now, today, on the local MEmu emulator
2. **Reference implementation** — its architecture (page graphs, recovery ladders, multi-backend device control) informs how State Cartographer should be built
3. **Corpus source** — its runs produce screenshots and logs used for offline analysis and VLM training

## Running ALAS

**Location:** `vendor/AzurLaneAutoScript/`

**Entry point:** `python gui.py` from the vendor directory

**Web UI:** `http://localhost:22267` (configurable in `config/deploy.yaml` under `Deploy.Webui`)

**Logs:** `vendor/AzurLaneAutoScript/log/{date}_gui.txt` for the GUI process, `{date}_{config_name}.txt` for task execution

**Healthy startup sequence:**
```
START (banner)
START (banner)                          ← EnableReload spawns a child process
Launcher config: Host, Port, SSL...
Webui configs: Theme, Language...
Started server process [PID]
Application startup complete.
```

If you see `[Errno 10048]` on port 22267 — a previous instance is still holding the port. Kill it first.

**Config:** `config/deploy.yaml` controls git, python, ADB, OCR, update, and webui settings. The active game config lives under `config/alas.json` (or whatever config name is selected in the UI).

**Vendor patches:** Three local patches are applied directly in the vendor dir (documented in [ALS-live-ops.md](ALS-live-ops.md)). These are unstaged edits that survive normal use but are wiped by `git submodule update --force`.

## Why ALAS Matters

ALAS matters because it proves the problem is real and tractable.

It gives the repo:
- a **working baseline** to run while the replacement is built
- mature operational prior art
- real workflow complexity and recovery patterns
- a concrete target for comparison
- evidence about what breaks in live automation, not just what looks clean on paper

## Conceptual Mapping

The mapping from ALAS concepts into repo concepts is still useful, but it is conceptual only.

| ALAS Component | Repo Concept |
|---|---|
| `module/ui/page.py` | explicit page/state knowledge |
| `module/ui/assets.py` | anchors, regions, and UI cues |
| `module/ui/ui.py` | locate + goto patterns |
| scheduler commands/tasks | assignment/workflow inventory |
| device control and screenshot layers | operator/runtime backend requirements |

This table is a reasoning aid. It is not a claim that equivalent repo code currently exists or is trustworthy.

## What Exists Today

The durable ALAS surfaces in this repo are:
- `vendor/AzurLaneAutoScript/`
- ALAS logs under `vendor/AzurLaneAutoScript/log/`
- local vendor patches described in `ALS-live-ops.md`
- screenshot/corpus artifacts under `data/` when collection has been run
- ALS reference docs in this folder

Do not assume older repo-side ALAS helper scripts still exist just because older docs or plans mention them. Most of that script surface has been deliberately removed.

## Key Findings Preserved From ALAS Work

- **ALAS labels are task-context labels, not pure visual labels**: a task/page name in ALAS does not necessarily mean the visible frame matches that label in a visually strict sense.
- **Black-frame behavior is operationally important**: black frames often point to screenshot/provider churn or recovery issues rather than simple page-classification failure.
- **Screenshot transport matters**: different screenshot methods materially change whether the system appears stable or inert.
- **Some failures are domain-specific and recurring**: certain Azur Lane flows repeatedly trigger distinct failure classes that are worth remembering as named problems.

## Operational Pointers

- active config is typically under `vendor/AzurLaneAutoScript/config/`
- logs are under `vendor/AzurLaneAutoScript/log/`
- live-run handling rules are in `ALS-live-ops.md`
- any future ALAS-derived event recording should be treated as unsettled until the runtime proves it needs a concrete schema

## How To Use ALAS Correctly

- Use it as reference architecture.
- Use it as a corpus and operational truth source.
- Use it to understand workflow complexity and failure modes.
- Do not treat its internal task/page names as automatically valid visual labels.
- Do not treat wrapping or launching ALAS as equivalent to the runtime this repo intends to build.
