"""Shared test fixtures for state-cartographer tests."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def make_rgb_png(pixels: list[tuple[int, int, int]], width: int, height: int) -> bytes:
    """Create a minimal, valid RGB PNG from pixel values (row-major order).

    Does not require Pillow — uses only stdlib struct and zlib.
    Useful for creating real image fixtures in tests that exercise PIL-based code.
    """

    def _chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    # IHDR: width, height, bit_depth=8, color_type=2 (RGB), compress=0, filter=0, interlace=0
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    # Raw image data: one filter byte (0=None) followed by RGB bytes per row
    raw = b"".join(
        b"\x00" + b"".join(bytes(p) for p in pixels[row * width : (row + 1) * width]) for row in range(height)
    )
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")

    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


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
