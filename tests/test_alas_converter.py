"""Integration tests for ALAS converter and schema alignment."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALAS_ROOT = REPO_ROOT / "vendor" / "AzurLaneAutoScript"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import contextlib  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402
from alas_converter import build_graph  # noqa: E402

from schema_validator import validate_graph  # noqa: E402


def test_alas_converter_build_graph_shape():
    if not ALAS_ROOT.exists():
        pytest.skip("ALAS submodule is not present")

    graph = build_graph(locale="en")
    assert graph["initial_state"] == "page_main"
    assert graph["metadata"]["app"] == "Azur Lane"
    assert graph["metadata"]["locale"] == "en"

    assert len(graph["states"]) == 43
    assert len(graph["transitions"]) == 105

    assert "page_unknown" in graph["states"]
    assert graph["states"]["page_unknown"]["anchors"] == []
    assert "page_main" in graph["states"]
    assert "page_main_white" in graph["states"]

    # All pages should have at least one anchor, except page_unknown
    for state_id, state_def in graph["states"].items():
        if state_id != "page_unknown":
            assert state_def["anchors"], f"{state_id} missing anchors"

    # All transitions should be deterministic and resolve to valid destinations.
    for transition_id, transition in graph["transitions"].items():
        assert transition["source"] in graph["states"], f"{transition_id} has unknown source"
        assert transition["dest"] in graph["states"], f"{transition_id} has unknown destination"
        assert transition["method"] == "deterministic"
        action = transition["action"]
        assert action["type"] == "adb_tap"
        assert isinstance(action["x"], int)
        assert isinstance(action["y"], int)


def test_alas_converter_cli_matches_validator():
    if not ALAS_ROOT.exists():
        pytest.skip("ALAS submodule is not present")

    output = REPO_ROOT / "examples" / "_tmp_alas_converter_graph.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "alas_converter.py"),
            "--locale",
            "en",
            "--serial",
            "127.0.0.1:21513",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    data = json.loads(output.read_text(encoding="utf-8"))
    assert validate_graph(data) == []
    assert data["metadata"]["app"] == "Azur Lane"
    assert len(data["states"]) == 43
    assert output.exists()
    with contextlib.suppress(OSError):
        output.unlink()
