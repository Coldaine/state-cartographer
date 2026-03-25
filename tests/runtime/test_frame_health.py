from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from runtime.observation.frame_health import analyze_image


class FrameHealthTests(unittest.TestCase):
    def _make_image(self, color: int) -> Path:
        target = Path(tempfile.mkdtemp()) / f"{color}.png"
        Image.new("L", (32, 32), color=color).save(target)
        return target

    def test_black_frame_detection(self) -> None:
        image = self._make_image(0)
        frame = analyze_image(image, black_threshold=2.0, near_black_threshold=8.0, stale_timeout_s=2.0)
        self.assertTrue(frame.health.is_black)

    def test_near_black_detection(self) -> None:
        image = self._make_image(6)
        frame = analyze_image(image, black_threshold=2.0, near_black_threshold=8.0, stale_timeout_s=2.0)
        self.assertTrue(frame.health.is_near_black)
        self.assertFalse(frame.health.is_black)

    def test_repeated_and_stale_detection(self) -> None:
        image = self._make_image(255)
        first = analyze_image(image, black_threshold=2.0, near_black_threshold=8.0, stale_timeout_s=0.1)
        second = analyze_image(
            image,
            previous_hash=first.frame_hash,
            previous_seen_at=first.captured_at_monotonic - 1.0,
            black_threshold=2.0,
            near_black_threshold=8.0,
            stale_timeout_s=0.1,
        )
        self.assertTrue(second.health.is_repeated)
        self.assertTrue(second.health.is_stale)


if __name__ == "__main__":
    unittest.main()
