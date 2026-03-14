"""Tests for execution_event_log.py."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from execution_event_log import append_event, load_events, make_event, validate_event  # noqa: E402


def test_make_event_builds_valid_execution_event():
    event = make_event(
        run_id="run-1",
        serial="127.0.0.1:21513",
        event_type="execution",
        ok=True,
        assignment="Commission",
        semantic_action="handle_popup_confirm",
        primitive_action="click",
        target="POPUP_CONFIRM",
    )

    assert event["event_type"] == "execution"
    assert event["assignment"] == "Commission"
    assert event["semantic_action"] == "handle_popup_confirm"
    assert event["primitive_action"] == "click"


def test_append_and_load_events_round_trip(tmp_path: Path):
    log_path = tmp_path / "events.jsonl"
    event = make_event(
        run_id="run-1",
        serial="127.0.0.1:21513",
        event_type="observation",
        ok=True,
        semantic_action="state_confirm",
        primitive_action="screenshot",
        state_after="page_main",
    )

    append_event(log_path, event)
    loaded = load_events(log_path)

    assert len(loaded) == 1
    assert loaded[0]["state_after"] == "page_main"
    assert loaded[0]["primitive_action"] == "screenshot"


def test_validate_event_rejects_missing_required_fields():
    bad_event = {
        "run_id": "run-1",
        "serial": "127.0.0.1:21513",
        "event_type": "execution",
        "ok": True,
    }
    del bad_event["serial"]

    try:
        validate_event(bad_event)
    except ValueError as exc:
        assert "Missing required event fields" in str(exc)
    else:
        raise AssertionError("validate_event should reject missing required fields")
