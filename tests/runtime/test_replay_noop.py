from __future__ import annotations

import unittest

from runtime.replay.noop import NoopReplay


class NoopReplayTests(unittest.TestCase):
    def test_lookup_returns_miss(self) -> None:
        replay = NoopReplay()
        result = replay.lookup("frame.png", "commission_collect")
        self.assertEqual(result.status, "miss")
        self.assertEqual(result.hint_status, "none")


if __name__ == "__main__":
    unittest.main()
