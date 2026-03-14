"""Minimal RGB PNG factory — no Pillow dependency.

Shared helper used by test modules and conftest fixtures.
"""

from __future__ import annotations

import struct
import zlib


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

    raw = b"".join(
        b"\x00" + b"".join(bytes(p) for p in pixels[row * width : (row + 1) * width]) for row in range(height)
    )
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")

    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend
