# ALAS Reference Code Instructions

The `vendor/AzurLaneAutoScript` submodule has been removed from this repository to reduce distraction and repo size.

## When You Need ALAS Reference Code

If you need to examine the original Azur Lane Auto Script codebase (for navigation graph extraction, page definitions, popup handlers, UI coordinates, or any other reference), clone it directly:

```bash
git clone https://github.com/LmeSzinc/AzurLaneAutoScript.git /tmp/ALAS_reference
```

Key files in ALAS:
- `module/ui/page.py` — Page definitions and navigation graph (43 pages, 107 edges)
- `module/ui/assets.py` — Button coordinates (95 buttons, EN region)
- `module/ui_white/assets.py` — White UI button coordinates (35 buttons)
- `module/ui/ui.py` — Navigation engine (ui_goto, ui_get_current_page, ui_additional)
- `module/base/button.py` — Button template matching implementation

## Existing Reference Documentation

The navigation graph and runtime architecture have already been extracted and documented in this repo:
- `docs/ALS-reference/ALS-navigation-graph.md` — Full navigation state machine with coordinates
- `docs/ALS-reference/ALS-runtime-architecture.md` — VLM-first runtime loop design
- `docs/ALS-reference/ALS-overview.md` — What ALAS is and why we're replacing it
- `docs/ALS-reference/ALS-live-ops.md` — Operational rules for running ALAS

Check these docs before cloning. The answer may already be extracted.
