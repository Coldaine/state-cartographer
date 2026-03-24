# Phase 1-3 Execution Report

> Historical note: moved from `docs/research/RES-phase1-3-report.md` during the 2026 documentation realignment.


> This document records the user-execution phases after Phase 0.
> It is not the repo roadmap and not the product skill/agent phase model.

## Scope

These phases were executed against the real Azur Lane + ALAS harness setup, using:

- `vendor/AzurLaneAutoScript/log/2026-03-14_PatrickCustom.txt`
- recent ALAS error screenshots under `vendor/AzurLaneAutoScript/log/error/`
- the current generated graph at `examples/azur-lane/graph.json`

## Phase 1: Live Harness Interrogation

Goal: prove that the external system is live enough to produce real runtime artifacts.

What was verified:

- The ALAS Windows harness artifacts exist locally:
  - `vendor/AzurLaneAutoScript/gui.py`
  - `vendor/AzurLaneAutoScript/.venv/Scripts/python.exe`
  - `vendor/AzurLaneAutoScript/config/PatrickCustom.json`
- Launching the documented ALAS harness path produced fresh log output in:
  - `vendor/AzurLaneAutoScript/log/2026-03-14_PatrickCustom.txt`
- The log shows ALAS actively interacting with Azur Lane:
  - task execution
  - app restart
  - login clicks
  - screenshot polling

Observed outcome:

- The harness did start and interact with the game.
- It did not complete cleanly.
- It fell into repeated `Restart` failures and ended with `Request human takeover`.

## Phase 2: Real Artifact Replay

Goal: run the repo's own observation/classification path on real ALAS-captured screenshots.

Method:

1. Parse the real ALAS log with `scripts/alas_log_parser.py`.
2. Take the latest real error screenshots from ALAS error directories.
3. Run `scripts/observe.py` logic over those PNGs.
4. Run `scripts/locate.py` against the current graph.

ALAS run summary from the parsed log:

- Session window:
  - start: `2026-03-14T00:43:55.361000`
  - end: `2026-03-14T01:31:52.498000`
- Error summary:
  - `critical_count`: 4
  - `error_count`: 12
  - `warning_count`: 201
- Dominant exception types:
  - `GameStuckError`: 8
  - `GameTooManyClickError`: 3
  - `TypeError`: 1

Real screenshot replay result:

- 9 recent ALAS error screenshots were classified.
- Result: all 9 returned:
  - `state = "unknown"`
  - `confidence = 0.0`
  - `message = "No matching state found. Observations match nothing in the graph."`

## Phase 3: Gap Confirmation

Goal: determine what the previous two phases imply about the current system state.

Confirmed conclusions:

1. The harness is real and producing runtime artifacts.
2. The repo can parse those artifacts.
3. The current graph and anchor set are not yet sufficient to orient on the recent real ALAS screenshots.

This means the immediate gap is not conceptual.
It is operational:

- the repo has a graph
- the repo has observation tooling
- the repo has classification tooling
- but the graph does not currently match recent live screenshots well enough to classify them

## Additional provider findings

- Windows-side `adb.exe` is available via the installed scrcpy package.
- The ADB daemon can start from the current WSL-mediated session.
- Direct repo-level probes to `127.0.0.1:21513` and `127.0.0.1:21503` refused connection at the times tested.
- So the live harness exists, but the repo's direct ADB attachment path was not yet attached to the emulator session during this execution.

## Exit State After Phase 3

Completed:

- Phase 0: target/tooling/provider boundary
- Phase 1: live harness interrogation
- Phase 2: real artifact replay
- Phase 3: gap confirmation against current graph

What these phases proved:

- The next work is not more abstract planning.
- The next work is to attach the repo's direct provider path to the live emulator and then capture a state-labeled dataset that the repo can classify or use to recalibrate anchors.

## Recommended next move

1. Make the repo's direct ADB path attach cleanly to the live emulator.
2. Capture fresh screenshots through the repo path, not only ALAS error dumps.
3. Re-run `observe.py` + `locate.py` on those screenshots.
4. If classification still fails, calibrate/update anchors using the newly attached live path.
