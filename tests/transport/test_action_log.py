"""Tests for best-effort transport action logging."""

from __future__ import annotations

from unittest.mock import Mock, patch

from state_cartographer.transport import action_log


def setup_function() -> None:
    action_log._logger = None
    action_log._session_id = None


def test_action_swallow_logger_setup_failure() -> None:
    with patch("state_cartographer.transport.action_log.start_session", side_effect=PermissionError("read only")):
        action_log.action("tap", "serial", "adb", {"x": 1}, "success")


def test_action_escapes_whitespace_and_newlines() -> None:
    logger = Mock()
    action_log._logger = logger
    action_log._session_id = "session"

    action_log.action(
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
    with patch("state_cartographer.transport.action_log._log_dir", return_value=tmp_path):
        logger = action_log._configure_logger("session_a")
        handler_count = len(logger.handlers)

        logger = action_log._configure_logger("session_b")

    assert logger.propagate is False
    assert len(logger.handlers) == handler_count
