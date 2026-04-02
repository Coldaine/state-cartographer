"""Tests for best-effort transport tracing."""

from __future__ import annotations

from unittest.mock import Mock, patch

from state_cartographer.transport import trace


def setup_function() -> None:
    trace._logger = None
    trace._session_id = None


def test_action_swallow_logger_setup_failure() -> None:
    with patch("state_cartographer.transport.trace.start_session", side_effect=PermissionError("read only")):
        trace.action("tap", "serial", "adb", {"x": 1}, "success")


def test_action_escapes_whitespace_and_newlines() -> None:
    logger = Mock()
    trace._logger = logger
    trace._session_id = "session"

    trace.action(
        "tap chain",
        "serial 1",
        "adb",
        {"note": "line one\nline two", "coords": {"x": 10, "y": 20}},
        "failure",
        error="bad input here",
    )

    message = logger.info.call_args[0][0]
    assert "\n" not in message
    assert "\t" in message
    assert "line\\u0020one\\nline\\u0020two" in message
    assert 'serial="serial\\u00201"' in message
    assert 'error="bad\\u0020input\\u0020here"' in message


def test_configure_logger_disables_propagation_and_reuses_handlers(tmp_path) -> None:
    with patch("state_cartographer.transport.trace._log_dir", return_value=tmp_path):
        logger = trace._configure_logger("session_a")
        handler_count = len(logger.handlers)

        logger = trace._configure_logger("session_b")

    assert logger.propagate is False
    assert len(logger.handlers) == handler_count
