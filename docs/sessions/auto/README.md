# Auto Session Summaries

This folder is the tracked summary surface for meaningful production runs.

Canonical local run artifacts stay under:

- `data/runs/<run_id>/manifest.json`
- `data/runs/<run_id>/events.ndjson`
- `data/runs/<run_id>/<lane>/...`
- `data/logs/<date>_<run_id>.log`

The files here are compact promoted summaries generated from those manifests.

Rules:

- keep these summaries small and reviewable
- promote only meaningful runs, not every scratch invocation
- treat `data/runs/` as the canonical local truth and this folder as the tracked index into that truth
