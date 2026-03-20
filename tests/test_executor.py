"""Tests for executor.py — task execution, auto session tracking, mock backend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from executor import execute_task, execute_task_by_id, mock_backend

# --- Fixtures ---


def make_session(current_state=None):
    return {
        "current_state": current_state,
        "history": [],
    }


def make_graph():
    """Minimal graph sufficient for navigation tests."""
    return {
        "states": {
            "page_main": {"anchors": [{"type": "pixel_color", "coords": [100, 100]}]},
            "page_commission": {"anchors": [{"type": "pixel_color", "coords": [200, 200]}]},
            "page_reward": {"anchors": [{"type": "pixel_color", "coords": [300, 300]}]},
        },
        "transitions": [],
    }


# --- Basic execution ---


class TestExecuteTask:
    def test_empty_actions(self):
        task = {
            "entry_state": "page_main",
            "actions": [],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        assert result["actions_completed"] == 0

    def test_navigates_to_entry_state(self):
        task = {
            "entry_state": "page_commission",
            "actions": [],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        # Should have navigated and confirmed state
        log = backend["_log"]
        nav_actions = [a for a in log if a["action"] == "navigate"]
        confirm_actions = [a for a in log if a["action"] == "session_confirm"]
        assert len(nav_actions) == 1
        assert nav_actions[0]["to"] == "page_commission"
        assert len(confirm_actions) == 1

    def test_skips_navigation_when_already_there(self):
        task = {
            "entry_state": "page_main",
            "actions": [],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        log = backend["_log"]
        nav_actions = [a for a in log if a["action"] == "navigate"]
        assert len(nav_actions) == 0

    def test_executes_tap_actions(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {"type": "tap", "coords": [640, 400]},
                {"type": "tap", "coords": [640, 600]},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        assert result["actions_completed"] == 2
        log = backend["_log"]
        taps = [a for a in log if a["action"] == "tap"]
        assert len(taps) == 2
        assert taps[0]["coords"] == (640, 400)
        assert taps[1]["coords"] == (640, 600)

    def test_executes_wait_action(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {"type": "wait", "seconds": 2.0},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        log = backend["_log"]
        sleeps = [a for a in log if a["action"] == "sleep"]
        assert len(sleeps) == 1
        assert sleeps[0]["seconds"] == 2.0

    def test_executes_navigate_action(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {"type": "navigate", "target_state": "page_commission"},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        log = backend["_log"]
        navs = [a for a in log if a["action"] == "navigate"]
        assert len(navs) == 1
        assert navs[0]["to"] == "page_commission"

    def test_executes_swipe_action(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {"type": "swipe", "start": [100, 500], "end": [100, 200]},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        log = backend["_log"]
        swipes = [a for a in log if a["action"] == "swipe"]
        assert len(swipes) == 1
        assert swipes[0]["start"] == (100, 500)
        assert swipes[0]["end"] == (100, 200)

    def test_orients_from_unknown_state_before_navigation(self):
        task = {
            "entry_state": "page_commission",
            "actions": [],
        }
        backend = mock_backend()
        session = make_session(None)

        def locate_main(**_kw):
            return {"state": "page_main", "confidence": 0.95}

        backend["locate"] = locate_main
        result = execute_task(task, make_graph(), session, backend)

        assert result["success"]
        log = backend["_log"]
        confirms = [a for a in log if a["action"] == "session_confirm"]
        navs = [a for a in log if a["action"] == "navigate"]
        assert confirms[0]["state"] == "page_main"
        assert navs[0]["from"] == "page_main"


# --- Error handling ---


class TestExecutorErrors:
    def test_navigation_failure(self):
        task = {
            "entry_state": "page_commission",
            "actions": [],
        }

        def failing_navigate(**_kw):
            return {"success": False, "error": "No route found"}

        backend = mock_backend()
        backend["navigate"] = failing_navigate
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert not result["success"]
        assert "Failed to navigate" in result["error"]

    def test_action_failure_stops_sequence(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {"type": "tap", "coords": [640, 400]},
                {"type": "assert_state", "expected_state": "page_reward"},
                {"type": "tap", "coords": [640, 600]},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert not result["success"]
        assert result["actions_completed"] == 1  # First tap succeeded
        assert "Expected state" in result["error"]

    def test_unknown_action_type(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {"type": "explode"},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert not result["success"]
        assert "Unknown action type" in result["error"]


# --- Repeat actions ---


class TestRepeatAction:
    def test_repeat_count(self):
        task = {
            "entry_state": "page_main",
            "actions": [
                {
                    "type": "repeat",
                    "count": 3,
                    "body": [
                        {"type": "tap", "coords": [640, 400]},
                        {"type": "wait", "seconds": 0.5},
                    ],
                },
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        log = backend["_log"]
        taps = [a for a in log if a["action"] == "tap"]
        sleeps = [a for a in log if a["action"] == "sleep"]
        assert len(taps) == 3
        assert len(sleeps) == 3


# --- Session auto-tracking ---


class TestAutoSessionTracking:
    def test_session_updated_after_navigation(self):
        task = {
            "entry_state": "page_commission",
            "actions": [
                {"type": "navigate", "target_state": "page_reward"},
            ],
        }
        backend = mock_backend()
        session = make_session("page_main")
        result = execute_task(task, make_graph(), session, backend)
        assert result["success"]
        # Session should reflect the final state
        confirms = [a for a in backend["_log"] if a["action"] == "session_confirm"]
        assert len(confirms) == 2  # Once for entry nav, once for action nav
        assert confirms[0]["state"] == "page_commission"
        assert confirms[1]["state"] == "page_reward"


class TestCanonicalEntrypoint:
    def test_execute_task_by_id_uses_mock_backend_without_preflight(self, tmp_path):
        tasks_path = tmp_path / "tasks.json"
        graph_path = tmp_path / "graph.json"

        tasks_path.write_text(
            json.dumps(
                {
                    "tasks": {
                        "commission": {
                            "entry_state": "page_main",
                            "actions": [{"type": "tap", "coords": [640, 360]}],
                        }
                    }
                }
            )
        )
        graph_path.write_text(json.dumps(make_graph()))

        result = execute_task_by_id(
            "commission",
            tasks_path,
            graph_path,
            backend_name="mock",
            preflight=False,
        )

        assert result["success"]
        assert result["entrypoint"] == "scripts/executor.py"
        assert result["backend"] == "mock"

    def test_execute_task_by_id_returns_error_for_unknown_task(self, tmp_path):
        tasks_path = tmp_path / "tasks.json"
        graph_path = tmp_path / "graph.json"

        tasks_path.write_text(json.dumps({"tasks": {}}))
        graph_path.write_text(json.dumps(make_graph()))

        result = execute_task_by_id(
            "missing",
            tasks_path,
            graph_path,
            backend_name="mock",
            preflight=False,
        )

        assert not result["success"]
        assert "not found" in result["error"]
