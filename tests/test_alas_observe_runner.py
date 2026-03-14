"""Tests for alas_observe_runner.py."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from alas_observe_runner import ObservationRuntime, infer_target_name  # noqa: E402
from execution_event_log import load_events  # noqa: E402
from png_factory import make_rgb_png  # noqa: E402


class _Button:
    def __init__(self, name: str):
        self.name = name


def test_infer_target_name_prefers_named_objects():
    button = _Button("GOTO_MAIN")
    assert infer_target_name((button,), {}) == "GOTO_MAIN"
    assert infer_target_name(("POPUP_CONFIRM",), {}) == "POPUP_CONFIRM"
    assert infer_target_name((), {}) is None


def test_observation_runtime_records_classified_screenshot(tmp_path: Path):
    graph = {
        "states": {
            "page_main": {
                "anchors": [
                    {"type": "pixel_color", "x": 0, "y": 0, "expected_rgb": [255, 0, 0]},
                ],
                "negative_anchors": [],
                "confidence_threshold": 0.7,
            }
        },
        "transitions": {},
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(__import__("json").dumps(graph), encoding="utf-8")

    runtime = ObservationRuntime(graph_path=graph_path, run_dir=tmp_path / "run")
    png_bytes = make_rgb_png([(255, 0, 0)], width=1, height=1)

    from PIL import Image
    import io

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    runtime.record_screenshot(serial="127.0.0.1:21513", image=image)

    assert runtime.session["current_state"] == "page_main"
    assert runtime.events_path.exists()
    assert runtime.observations_path.exists()
    assert runtime.session_path.exists()

    events = load_events(runtime.events_path)
    assert events[-1]["state_before"] is None
    assert events[-1]["state_after"] == "page_main"


def test_record_action_clears_current_state_after_successful_transition(tmp_path: Path):
    graph = {"states": {"page_main": {"anchors": [], "negative_anchors": []}}, "transitions": {}}
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(__import__("json").dumps(graph), encoding="utf-8")

    runtime = ObservationRuntime(graph_path=graph_path, run_dir=tmp_path / "run")
    runtime.session["current_state"] = "page_main"

    runtime.record_action(
        serial="127.0.0.1:21513",
        event_type="execution",
        semantic_action="click",
        primitive_action="click",
        target="GOTO_MAIN",
        ok=True,
        duration_ms=12,
    )

    assert runtime.session["current_state"] is None
    assert runtime.session["history"][-1]["type"] == "transition"
    assert runtime.session["history"][-1]["transition_id"] == "click:GOTO_MAIN"

    events = load_events(runtime.events_path)
    assert events[-1]["state_before"] == "page_main"
    assert events[-1]["state_after"] is None


def test_record_page_confirmation_ignores_unmodeled_states(tmp_path: Path):
    graph = {"states": {"page_main": {"anchors": [], "negative_anchors": []}}, "transitions": {}}
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(__import__("json").dumps(graph), encoding="utf-8")

    runtime = ObservationRuntime(graph_path=graph_path, run_dir=tmp_path / "run")
    runtime.record_page_confirmation(serial="127.0.0.1:21513", page_name="page_vendor_only")

    assert runtime.session["current_state"] is None
    events = load_events(runtime.events_path)
    assert events[-1]["event_type"] == "recovery"
    assert events[-1]["semantic_action"] == "unmodeled_page_observed"


def test_run_passively_swallows_system_exit_and_logs_recovery(tmp_path: Path):
    graph = {"states": {"page_main": {"anchors": [], "negative_anchors": []}}, "transitions": {}}
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(__import__("json").dumps(graph), encoding="utf-8")

    runtime = ObservationRuntime(graph_path=graph_path, run_dir=tmp_path / "run")

    def _boom():
        raise SystemExit(2)

    result = runtime.run_passively(
        event_serial="127.0.0.1:21513",
        observer_name="record_screenshot",
        func=_boom,
    )

    assert result is None
    events = load_events(runtime.events_path)
    assert events[-1]["event_type"] == "recovery"
    assert events[-1]["semantic_action"] == "observer_error"
    assert events[-1]["error"] == "SystemExit"
