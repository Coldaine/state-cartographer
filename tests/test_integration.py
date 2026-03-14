"""Integration tests — verify tools work together on example graphs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def run_script(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def assert_success(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"


class TestValidatorIntegration:
    def test_template_graph_valid(self):
        result = run_script("schema_validator.py", str(EXAMPLES_DIR / "template" / "graph.json"))
        assert_success(result)
        assert "Valid" in result.stdout

    def test_simple_web_form_valid(self):
        result = run_script("schema_validator.py", str(EXAMPLES_DIR / "simple-web-form" / "graph.json"))
        assert_success(result)
        assert "Valid" in result.stdout

    def test_invalid_graph_fails(self, tmp_path):
        bad_graph = tmp_path / "bad.json"
        bad_graph.write_text('{"states": {}, "transitions": {"t1": {"source": "missing"}}}')
        result = run_script("schema_validator.py", str(bad_graph))
        assert result.returncode == 1

    def test_missing_graph_file_fails_cleanly(self, tmp_path):
        missing_graph = tmp_path / "missing.json"
        result = run_script("schema_validator.py", str(missing_graph))
        assert result.returncode == 2
        assert "File not found" in result.stderr

    def test_invalid_json_fails_cleanly(self, tmp_path):
        bad_graph = tmp_path / "bad-json.json"
        bad_graph.write_text("{bad json")
        result = run_script("schema_validator.py", str(bad_graph))
        assert result.returncode == 2
        assert "Invalid JSON" in result.stderr


class TestGraphUtilsIntegration:
    def test_summary(self):
        result = run_script(
            "graph_utils.py", "--graph", str(EXAMPLES_DIR / "simple-web-form" / "graph.json"), "summary"
        )
        assert_success(result)
        data = json.loads(result.stdout)
        assert data["total_states"] == 7
        assert data["total_transitions"] == 11

    def test_states(self):
        result = run_script("graph_utils.py", "--graph", str(EXAMPLES_DIR / "simple-web-form" / "graph.json"), "states")
        assert_success(result)
        states = json.loads(result.stdout)
        assert "dashboard" in states
        assert len(states) == 7


class TestPathfindIntegration:
    def test_find_route(self):
        result = run_script(
            "pathfind.py",
            "--graph",
            str(EXAMPLES_DIR / "simple-web-form" / "graph.json"),
            "--from",
            "landing_page",
            "--to",
            "settings",
        )
        assert_success(result)
        data = json.loads(result.stdout)
        assert data["hops"] >= 2
        assert data["total_cost"] > 0

    def test_prefer_deterministic(self):
        result = run_script(
            "pathfind.py",
            "--graph",
            str(EXAMPLES_DIR / "simple-web-form" / "graph.json"),
            "--from",
            "landing_page",
            "--to",
            "profile_edit",
            "--prefer",
            "deterministic",
        )
        assert_success(result)
        data = json.loads(result.stdout)
        # landing_page → login_form (det) → dashboard (vision) → profile_edit (det) = 3 hops
        assert data["hops"] == 3
        assert data["hops"] == len(data["route"])
        assert data["deterministic_steps"] == 2
        assert data["vision_steps"] == 1


class TestSessionIntegration:
    def test_init_session(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text('{"states": {}, "transitions": {}}')
        session_file = tmp_path / "session.json"
        result = run_script("session.py", "init", "--graph", str(graph), "--output", str(session_file))
        assert_success(result)
        assert session_file.exists()
        data = json.loads(session_file.read_text())
        assert data["current_state"] is None
        assert data["history"] == []

    def test_confirm_state(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text('{"states": {}, "transitions": {}}')
        session_file = tmp_path / "session.json"
        run_script("session.py", "init", "--graph", str(graph), "--output", str(session_file))
        result = run_script("session.py", "confirm", "--session", str(session_file), "--state", "main_menu")
        assert_success(result)
        data = json.loads(session_file.read_text())
        assert data["current_state"] == "main_menu"

    def test_record_transition(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text('{"states": {}, "transitions": {}}')
        session_file = tmp_path / "session.json"
        run_script("session.py", "init", "--graph", str(graph), "--output", str(session_file))
        run_script("session.py", "confirm", "--session", str(session_file), "--state", "main_menu")
        result = run_script("session.py", "transition", "--session", str(session_file), "--event", "tap_dock")
        assert_success(result)
        data = json.loads(session_file.read_text())
        assert data["current_state"] is None
        assert any(h["type"] == "transition" for h in data["history"])

    def test_query_session(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text('{"states": {}, "transitions": {}}')
        session_file = tmp_path / "session.json"
        run_script("session.py", "init", "--graph", str(graph), "--output", str(session_file))
        run_script("session.py", "confirm", "--session", str(session_file), "--state", "dock")
        result = run_script("session.py", "query", "--session", str(session_file))
        assert_success(result)
        data = json.loads(result.stdout)
        assert data["current_state"] == "dock"


class TestObserveIntegration:
    def test_observe_screenshot_no_graph(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake png data")
        result = run_script("observe.py", "--screenshot", str(screenshot))
        assert_success(result)
        data = json.loads(result.stdout)
        assert "screenshot" in data
        assert "pixels" in data
        assert data["pixels"] == {}

    def test_observe_screenshot_with_graph(self, tmp_path):
        screenshot = tmp_path / "screen.png"
        screenshot.write_bytes(b"fake png data")
        graph = tmp_path / "graph.json"
        graph.write_text('{"states": {"s1": {"anchors": [{"type": "text_match", "pattern": "x"}]}}, "transitions": {}}')
        result = run_script("observe.py", "--screenshot", str(screenshot), "--graph", str(graph))
        assert_success(result)
        data = json.loads(result.stdout)
        # No pixel_color anchors in graph → pixels dict empty
        assert data["pixels"] == {}

    def test_observe_missing_screenshot(self, tmp_path):
        result = run_script("observe.py", "--screenshot", str(tmp_path / "missing.png"))
        assert result.returncode == 2


class TestFixtureGraphsValid:
    """Validate all fixture graphs pass schema validation."""

    @pytest.mark.parametrize(
        "graph_file",
        [
            "simple-linear.json",
            "branching.json",
            "with-anchors.json",
        ],
    )
    def test_fixture_graph(self, graph_file):
        fixture_path = Path(__file__).parent / "fixtures" / "graphs" / graph_file
        result = run_script("schema_validator.py", str(fixture_path))
        assert result.returncode == 0, f"Validation failed for {graph_file}: {result.stderr}"
