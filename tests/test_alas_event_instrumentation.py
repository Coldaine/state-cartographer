"""Tests for alas_event_instrumentation.py."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from alas_event_instrumentation import instrument_method  # noqa: E402
from execution_event_log import load_events  # noqa: E402


class _Config:
    Emulator_Serial = "127.0.0.1:21513"
    task = "Commission"


class _Dummy:
    config = _Config()

    def click(self, button):
        return f"clicked:{button}"

    def fail(self, button):
        raise RuntimeError(f"boom:{button}")


def test_instrument_method_logs_success(tmp_path: Path):
    log_path = tmp_path / "events.jsonl"
    instrument_method(
        _Dummy,
        "click",
        log_path=log_path,
        run_id="run-1",
        event_type="execution",
        semantic_action="click",
        primitive_action="click",
    )

    dummy = _Dummy()
    assert dummy.click("GOTO_MAIN") == "clicked:GOTO_MAIN"

    events = load_events(log_path)
    assert len(events) == 1
    assert events[0]["assignment"] == "Commission"
    assert events[0]["serial"] == "127.0.0.1:21513"
    assert events[0]["semantic_action"] == "click"
    assert events[0]["primitive_action"] == "click"
    assert events[0]["target"] == "GOTO_MAIN"
    assert events[0]["ok"] is True


def test_instrument_method_logs_failure(tmp_path: Path):
    log_path = tmp_path / "events.jsonl"
    instrument_method(
        _Dummy,
        "fail",
        log_path=log_path,
        run_id="run-1",
        event_type="execution",
        semantic_action="fail",
        primitive_action="click",
    )

    dummy = _Dummy()
    try:
        dummy.fail("POPUP_CONFIRM")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError from instrumented method")

    events = load_events(log_path)
    assert len(events) == 1
    assert events[0]["ok"] is False
    assert events[0]["error"] == "RuntimeError"
    assert events[0]["target"] == "POPUP_CONFIRM"
