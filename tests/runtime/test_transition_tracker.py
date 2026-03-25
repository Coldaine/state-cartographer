from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from runtime.controller.transition_tracker import TransitionTracker
from runtime.observation.frame_health import analyze_image


class TransitionTrackerTests(unittest.TestCase):
    def _frame(self, color: int):
        path = Path(tempfile.mkdtemp()) / f"{color}.png"
        Image.new("L", (32, 32), color=color).save(path)
        return analyze_image(path, black_threshold=2.0, near_black_threshold=8.0, stale_timeout_s=1.0)

    def test_transition_in_progress_wins(self) -> None:
        tracker = TransitionTracker()
        before = self._frame(255)
        after = self._frame(200)
        self.assertEqual(tracker.classify(before, after, "transition_in_progress").value, "transition_state")


if __name__ == "__main__":
    unittest.main()
