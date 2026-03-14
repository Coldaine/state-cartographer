"""Tests for alas_corpus_summarize.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from alas_corpus_summarize import summarize_run  # noqa: E402
from png_factory import make_rgb_png  # noqa: E402


def _write_ndjson(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def test_summarize_run_counts_states_assignments_and_mismatches(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260314T000000Z-PatrickCustom"
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(parents=True)

    # Minimal graph: states are a dict in this repo's schema.
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "initial_state": "page_main",
                "metadata": {},
                "states": {"page_main": {"anchors": []}},
                "transitions": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    (run_dir / "meta.json").write_text(
        json.dumps({"run_id": "run-1", "graph_path": str(graph_path), "created_at": "2026-03-14T00:00:00+00:00"})
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "session.json").write_text(
        json.dumps(
            {
                "graph_path": str(graph_path),
                "created_at": "2026-03-14T00:00:00+00:00",
                "current_state": "page_main",
                "history": [
                    {"type": "confirmed_state", "state_id": "page_main", "timestamp": "2026-03-14T00:00:01+00:00"}
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    # Two screenshots exist on disk, one observation references a missing screenshot.
    (screenshots_dir / "000001.png").write_bytes(make_rgb_png([(0, 0, 0)], 1, 1))
    (screenshots_dir / "000002.png").write_bytes(make_rgb_png([(255, 0, 0)], 1, 1))

    observations = [
        {
            "timestamp": "2026-03-14T00:00:02+00:00",
            "assignment": "Commission",
            "screenshot": str(screenshots_dir / "000001.png"),
            "locate_result": {"state": "page_main"},
            "current_state": "page_main",
        },
        {
            "timestamp": "2026-03-14T00:00:03+00:00",
            "assignment": "Commission",
            "screenshot": str(screenshots_dir / "000999.png"),
            "locate_result": {"state": "unknown"},
            "current_state": "page_main",
        },
        # Deliberate inconsistency: locate_result says page_main but current_state differs.
        {
            "timestamp": "2026-03-14T00:00:04+00:00",
            "assignment": "Commission",
            "screenshot": str(screenshots_dir / "000002.png"),
            "locate_result": {"state": "page_main"},
            "current_state": "page_other",
        },
    ]
    _write_ndjson(run_dir / "observations.jsonl", observations)

    events = [
        {
            "ts": "2026-03-14T00:00:01+00:00",
            "run_id": "run-1",
            "session_id": None,
            "serial": "127.0.0.1:21513",
            "assignment": "Commission",
            "event_type": "assignment",
            "semantic_action": "assignment_start",
            "primitive_action": None,
            "target": "Commission",
            "coords": None,
            "gesture": None,
            "package": None,
            "state_before": None,
            "state_after": None,
            "screen_before": None,
            "screen_after": None,
            "ok": True,
            "duration_ms": 0,
            "error": None,
            "notes": None,
        },
        {
            "ts": "2026-03-14T00:00:05+00:00",
            "run_id": "run-1",
            "session_id": None,
            "serial": "127.0.0.1:21513",
            "assignment": "Commission",
            "event_type": "execution",
            "semantic_action": "click",
            "primitive_action": "click",
            "target": "BTN_OK",
            "coords": [1, 2],
            "gesture": None,
            "package": None,
            "state_before": "page_main",
            "state_after": None,
            "screen_before": None,
            "screen_after": None,
            "ok": True,
            "duration_ms": 12,
            "error": None,
            "notes": None,
        },
        # Event state_after not in graph should be reported.
        {
            "ts": "2026-03-14T00:00:06+00:00",
            "run_id": "run-1",
            "session_id": None,
            "serial": "127.0.0.1:21513",
            "assignment": "Commission",
            "event_type": "observation",
            "semantic_action": "ui_get_current_page",
            "primitive_action": None,
            "target": "page_shop",
            "coords": None,
            "gesture": None,
            "package": None,
            "state_before": "page_main",
            "state_after": "page_shop",
            "screen_before": None,
            "screen_after": None,
            "ok": True,
            "duration_ms": 0,
            "error": None,
            "notes": None,
        },
    ]
    _write_ndjson(run_dir / "events.jsonl", events)

    summary = summarize_run(run_dir, graph_path=graph_path, top_n=10)

    assert summary["run_id"] == "run-1"
    assert summary["counts"]["screenshots_on_disk"] == 2
    assert summary["counts"]["observations"] == 3
    assert summary["counts"]["events"] == 3

    assert summary["states"]["by_locate_state"]["page_main"] == 2
    assert summary["states"]["by_locate_state"]["unknown"] == 1
    assert summary["states"]["unknown_rate"] == 1 / 3

    assert summary["assignments"]["starts"]["Commission"] == 1

    assert summary["mismatches"]["missing_screenshot_files"] == 1
    assert summary["mismatches"]["inconsistent_current_state"] == 1
    assert "page_shop" in summary["mismatches"]["event_states_not_in_graph"]

