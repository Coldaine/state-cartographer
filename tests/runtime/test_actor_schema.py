from __future__ import annotations

import unittest

from runtime.actor.schema import ActionType, parse_actor_decision


class ActorSchemaTests(unittest.TestCase):
    def test_parse_valid_candidate_set(self) -> None:
        decision = parse_actor_decision(
            {
                "screen_label": "commission_screen",
                "transition_state": "stable_state",
                "candidates": [
                    {
                        "action_type": "tap",
                        "confidence": 0.9,
                        "uncertainty": 0.1,
                        "rationale": "Bell icon is visible.",
                        "target_point": {"x": 0.25, "y": 0.8},
                        "bbox": [0.2, 0.75, 0.3, 0.85],
                    }
                ],
            }
        )
        self.assertEqual(decision.candidates[0].action_type, ActionType.TAP)

    def test_reject_invalid_bbox(self) -> None:
        with self.assertRaises(ValueError):
            parse_actor_decision(
                {
                    "screen_label": "bad",
                    "transition_state": "stable_state",
                    "candidates": [
                        {
                            "action_type": "tap",
                            "confidence": 0.9,
                            "uncertainty": 0.1,
                            "rationale": "Bad box.",
                            "target_point": {"x": 0.25, "y": 0.8},
                            "bbox": [0.4, 0.75, 0.3, 0.85],
                        }
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
