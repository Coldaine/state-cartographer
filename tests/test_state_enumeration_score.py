from __future__ import annotations

import json
import sys
from pathlib import Path

from png_factory import make_rgb_png

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from state_enumeration_score import score_runs  # noqa: E402


def _write_png(path: Path, rgb: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_rgb_png([rgb], width=1, height=1))


def test_score_runs_discards_junk_loops_and_counts_labeled_states(tmp_path: Path, monkeypatch):
    import screenshot_dedupe

    monkeypatch.setattr(screenshot_dedupe, "_load_vision_backend", lambda: None)

    run_dir = tmp_path / "run"
    screenshots = run_dir / "screenshots"
    screenshots.mkdir(parents=True)

    _write_png(screenshots / "000001.png", (0, 0, 0))
    _write_png(screenshots / "000002.png", (0, 0, 0))
    _write_png(screenshots / "000003.png", (255, 0, 0))
    _write_png(screenshots / "000004.png", (255, 0, 0))
    _write_png(screenshots / "000005.png", (0, 0, 255))

    (run_dir / "observations.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "screenshot": str((screenshots / "000001.png").resolve()),
                        "locate_result": {"state": "unknown"},
                        "current_state": None,
                    }
                ),
                json.dumps(
                    {
                        "screenshot": str((screenshots / "000002.png").resolve()),
                        "locate_result": {"state": "unknown"},
                        "current_state": None,
                    }
                ),
                json.dumps(
                    {
                        "screenshot": str((screenshots / "000003.png").resolve()),
                        "locate_result": {"state": "unknown"},
                        "current_state": "page_guild",
                    }
                ),
                json.dumps(
                    {
                        "screenshot": str((screenshots / "000004.png").resolve()),
                        "locate_result": {"state": "unknown"},
                        "current_state": "page_guild",
                    }
                ),
                json.dumps(
                    {
                        "screenshot": str((screenshots / "000005.png").resolve()),
                        "locate_result": {"state": "unknown"},
                        "current_state": None,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    graph = {
        "states": {
            "page_guild": {
                "anchors": [
                    {"type": "pixel_color", "x": 0, "y": 0, "expected_rgb": [255, 0, 0]},
                ],
                "negative_anchors": [],
                "confidence_threshold": 0.7,
            }
        },
        "transitions": {},
    }
    graph_path = run_dir / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    (run_dir / "meta.json").write_text(json.dumps({"graph_path": str(graph_path.resolve())}), encoding="utf-8")

    report = score_runs(
        [run_dir],
        cluster_threshold=0,
        low_signal_mean=8.0,
        low_signal_stddev=6.0,
        target=50,
    )

    assert report["total_screenshots"] == 5
    assert report["junk_screenshots"] == 2
    assert report["usable_screenshots"] == 3
    assert report["labeled_states"] == ["page_guild"]
    assert report["candidate_unlabeled_clusters"] == 1
    assert report["estimated_enumerated_states"] == 2
