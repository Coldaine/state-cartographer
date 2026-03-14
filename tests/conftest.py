"""Shared test fixtures for state-cartographer tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from png_factory import make_rgb_png  # noqa: F401 — re-exported for backward compat

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def simple_linear_graph():
    with open(FIXTURES_DIR / "graphs" / "simple-linear.json") as f:
        return json.load(f)


@pytest.fixture
def branching_graph():
    with open(FIXTURES_DIR / "graphs" / "branching.json") as f:
        return json.load(f)


@pytest.fixture
def full_graph():
    with open(FIXTURES_DIR / "graphs" / "with-anchors.json") as f:
        return json.load(f)


@pytest.fixture
def empty_session():
    return {
        "graph_path": "test.json",
        "created_at": "2026-03-13T00:00:00Z",
        "current_state": None,
        "history": [],
    }


@pytest.fixture
def mid_session():
    return {
        "graph_path": "test.json",
        "created_at": "2026-03-13T00:00:00Z",
        "current_state": "dock",
        "history": [
            {"type": "confirmed_state", "state_id": "main_menu", "timestamp": "2026-03-13T00:01:00Z"},
            {
                "type": "transition",
                "transition_id": "main_to_dock",
                "from_state": "main_menu",
                "timestamp": "2026-03-13T00:02:00Z",
            },
            {"type": "confirmed_state", "state_id": "dock", "timestamp": "2026-03-13T00:03:00Z"},
        ],
    }
