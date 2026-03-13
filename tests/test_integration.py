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
        bad_graph.write_text('{bad json')
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
        assert data["route"] is not None


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
