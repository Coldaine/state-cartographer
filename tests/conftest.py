"""Shared test fixtures for surviving corpus-pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from png_factory import make_rgb_png  # noqa: F401 — re-exported for backward compat

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR
