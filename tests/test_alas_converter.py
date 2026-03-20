"""Integration tests for ALAS converter and schema alignment."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALAS_ROOT = REPO_ROOT / "vendor" / "AzurLaneAutoScript"
ALAS_PAGE_PY = ALAS_ROOT / "module" / "ui" / "page.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import contextlib  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402

from alas_converter import (  # noqa: E402
    _parse_locale_dict,
    build_graph,
    region_center,
)
from schema_validator import validate_graph  # noqa: E402


def require_alas_page_source() -> None:
    """Skip integration coverage unless the checked-out ALAS page source exists."""
    if not ALAS_PAGE_PY.exists():
        pytest.skip("ALAS page source is not present")


def test_alas_converter_build_graph_shape():
    require_alas_page_source()

    graph = build_graph(locale="en")
    assert graph["initial_state"] == "page_main"
    assert graph["metadata"]["app"] == "Azur Lane"
    assert graph["metadata"]["locale"] == "en"

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
    require_alas_page_source()

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
    assert output.exists()
    with contextlib.suppress(OSError):
        output.unlink()


def test_build_graph_raises_helpful_error_when_alas_missing(monkeypatch: pytest.MonkeyPatch):
    missing_page = REPO_ROOT / "vendor" / "_missing" / "module" / "ui" / "page.py"
    monkeypatch.setattr("alas_converter.PAGE_PY", missing_page)

    with pytest.raises(FileNotFoundError, match="git submodule update --init vendor/AzurLaneAutoScript") as exc_info:
        build_graph(locale="en")

    assert str(missing_page) in str(exc_info.value)


# ---------------------------------------------------------------------------
# Unit tests — no ALAS submodule required
# ---------------------------------------------------------------------------


class TestRegionCenter:
    """region_center() computes the integer center of an (x1, y1, x2, y2) box."""

    def test_even_dimensions(self):
        assert region_center((0, 0, 100, 100)) == (50, 50)

    def test_odd_dimensions_floor_divides(self):
        # Integer division: (0+101)//2 == 50
        assert region_center((0, 0, 101, 101)) == (50, 50)

    def test_offset_origin(self):
        assert region_center((10, 20, 110, 220)) == (60, 120)

    def test_already_at_center(self):
        # Non-trivial: box at offset with equal-width sides
        assert region_center((10, 20, 90, 180)) == (50, 100)

    def test_returns_ints(self):
        cx, cy = region_center((0, 0, 99, 99))
        assert cx == 49 and cy == 49  # (0+99)//2 == 49
        assert isinstance(cx, int)
        assert isinstance(cy, int)


class TestParseLocaleDict:
    """_parse_locale_dict() safely evaluates a Python dict literal."""

    def test_parses_string_values(self):
        result = _parse_locale_dict("{'en': 'hello', 'cn': 'world'}")
        assert result == {"en": "hello", "cn": "world"}

    def test_parses_tuple_values(self):
        result = _parse_locale_dict("{'en': (1, 2, 3), 'cn': (4, 5, 6)}")
        assert result["en"] == (1, 2, 3)
        assert result["cn"] == (4, 5, 6)

    def test_parses_nested_tuple_area(self):
        # area and button dicts use (x1, y1, x2, y2) tuples
        raw = "{'en': (46, 286, 265, 322), 'cn': (46, 286, 265, 322)}"
        result = _parse_locale_dict(raw)
        assert result["en"] == (46, 286, 265, 322)

    def test_raises_on_invalid_literal(self):
        import pytest

        with pytest.raises((ValueError, SyntaxError)):
            _parse_locale_dict("not a dict at all {{{")
