"""Tests for locate.py — Passive State Classifier."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from locate import (
    check_negative_anchors,
    constrain_by_session,
    evaluate_anchors,
    locate,
)


class TestEvaluateAnchors:
    def test_text_match(self):
        anchors = [{"type": "text_match", "pattern": "Welcome", "cost": 1}]
        obs = {"text_content": "Welcome, Commander"}
        score = evaluate_anchors("test", anchors, obs)
        assert score == 1.0

    def test_no_match(self):
        anchors = [{"type": "text_match", "pattern": "Goodbye", "cost": 1}]
        obs = {"text_content": "Welcome, Commander"}
        score = evaluate_anchors("test", anchors, obs)
        assert score == 0.0

    def test_dom_element_match(self):
        anchors = [{"type": "dom_element", "selector": "#header", "cost": 1}]
        obs = {"dom_elements": ["#header", "#footer"]}
        score = evaluate_anchors("test", anchors, obs)
        assert score == 1.0

    def test_empty_anchors(self):
        score = evaluate_anchors("test", [], {})
        assert score == 0.0

    def test_screenshot_region_skipped_without_screenshot(self):
        # screenshot_region anchor with no screenshot in observations → skipped, score based on remaining
        anchors = [
            {"type": "text_match", "pattern": "Hello", "cost": 1},
            {
                "type": "screenshot_region",
                "region": {"x": 0, "y": 0, "width": 10, "height": 10},
                "hash": "deadbeef01234567",
                "hash_algorithm": "phash",
                "threshold": 10,
                "cost": 5,
            },
        ]
        obs = {"text_content": "Hello World"}  # no "screenshot" key
        score = evaluate_anchors("test", anchors, obs)
        # screenshot_region is skipped → evaluated=1 (text_match), matches=1 → 1.0
        assert score == 1.0

    def test_screenshot_region_skipped_without_hash(self):
        # screenshot_region anchor with no stored hash → skipped (anchor not yet learned)
        anchors = [
            {"type": "text_match", "pattern": "Hello", "cost": 1},
            {"type": "screenshot_region", "region": {"x": 0, "y": 0, "width": 10, "height": 10}, "cost": 5},
        ]
        obs = {"text_content": "Hello World", "screenshot": "/fake/path.png"}
        score = evaluate_anchors("test", anchors, obs)
        # no hash → screenshot_region skipped, only text_match evaluated
        assert score == 1.0

    def test_score_excludes_unevaluatable_anchors(self):
        # Mixed anchors: text_match hits, screenshot_region skipped → score is 1.0, not 0.5
        anchors = [
            {"type": "text_match", "pattern": "Match", "cost": 1},
            {
                "type": "screenshot_region",
                "region": {"x": 0, "y": 0, "width": 10, "height": 10},
                "hash": "deadbeef01234567",
                "hash_algorithm": "phash",
                "threshold": 10,
                "cost": 5,
            },
        ]
        obs = {"text_content": "Match found"}  # no screenshot → region skipped
        score = evaluate_anchors("test", anchors, obs)
        # Old behavior would give 0.5 (1/2); new behavior gives 1.0 (1/1)
        assert score == 1.0

    def test_partial_match(self):
        anchors = [
            {"type": "text_match", "pattern": "Welcome", "cost": 1},
            {"type": "dom_element", "selector": "#missing", "cost": 2},
        ]
        obs = {"text_content": "Welcome", "dom_elements": []}
        score = evaluate_anchors("test", anchors, obs)
        assert score == 0.5

    def test_pixel_color_match(self):
        # pixel_color anchor evaluated directly from obs["pixels"] dict — no image needed
        anchors = [{"type": "pixel_color", "x": 10, "y": 20, "expected_rgb": [255, 0, 128], "cost": 1}]
        obs = {"pixels": {"10,20": [255, 0, 128]}}
        score = evaluate_anchors("test", anchors, obs)
        assert score == 1.0

    def test_pixel_color_no_match(self):
        anchors = [{"type": "pixel_color", "x": 10, "y": 20, "expected_rgb": [255, 0, 0], "cost": 1}]
        obs = {"pixels": {"10,20": [0, 255, 0]}}  # wrong color
        score = evaluate_anchors("test", anchors, obs)
        assert score == 0.0

    def test_pixel_color_missing_coordinate(self):
        # Coordinate present in anchor but not sampled in observations
        anchors = [{"type": "pixel_color", "x": 10, "y": 20, "expected_rgb": [255, 0, 0], "cost": 1}]
        obs = {"pixels": {}}  # nothing sampled
        score = evaluate_anchors("test", anchors, obs)
        assert score == 0.0

    def test_pixel_color_partial_match(self):
        # 2 pixel_color anchors, only 1 matches
        anchors = [
            {"type": "pixel_color", "x": 0, "y": 0, "expected_rgb": [255, 0, 0], "cost": 1},
            {"type": "pixel_color", "x": 1, "y": 0, "expected_rgb": [0, 255, 0], "cost": 1},
        ]
        obs = {"pixels": {"0,0": [255, 0, 0], "1,0": [0, 0, 255]}}  # second coord wrong
        score = evaluate_anchors("test", anchors, obs)
        assert score == 0.5


class TestNegativeAnchors:
    def test_negative_match_disqualifies(self):
        neg = [{"type": "dom_element", "selector": ".loading-spinner"}]
        obs = {"dom_elements": [".loading-spinner"]}
        assert check_negative_anchors("test", neg, obs) is True

    def test_no_negative_match(self):
        neg = [{"type": "dom_element", "selector": ".loading-spinner"}]
        obs = {"dom_elements": ["#content"]}
        assert check_negative_anchors("test", neg, obs) is False


class TestConstrainBySession:
    def test_empty_session(self, full_graph, empty_session):
        result = constrain_by_session(full_graph, empty_session)
        assert result is None

    def test_session_with_transition(self, full_graph):
        session = {"history": [{"type": "transition", "transition_id": "main_to_dock", "from_state": "main_menu"}]}
        result = constrain_by_session(full_graph, session)
        assert result == ["dock"]

    def test_session_with_confirmed_state(self, full_graph):
        session = {"history": [{"type": "confirmed_state", "state_id": "formation"}]}
        result = constrain_by_session(full_graph, session)
        assert result == ["formation"]


class TestLocate:
    def test_clear_match(self, full_graph, empty_session):
        obs = {
            "text_content": "Welcome, Commander",
            "dom_elements": ["#main-menu-container"],
        }
        result = locate(full_graph, empty_session, obs)
        assert result["state"] == "main_menu"
        assert result["confidence"] == 1.0

    def test_no_match_returns_unknown(self, full_graph, empty_session):
        obs = {"text_content": "Something completely different", "dom_elements": []}
        result = locate(full_graph, empty_session, obs)
        assert result["state"] == "unknown"

    def test_session_constrains_candidates(self, full_graph):
        session = {"history": [{"type": "transition", "transition_id": "main_to_dock", "from_state": "main_menu"}]}
        obs = {"text_content": "Dock", "dom_elements": ["#dock-header"]}
        result = locate(full_graph, session, obs)
        assert result["state"] == "dock"

    def test_ambiguous_returns_candidates(self, full_graph, empty_session):
        # "Dock Formation" hits one anchor each in dock and formation — tied at 0.5, both below threshold 0.7
        obs = {"text_content": "Dock Formation", "dom_elements": []}
        result = locate(full_graph, empty_session, obs)
        assert "candidates" in result, f"Expected ambiguous result, got: {result}"
        candidate_states = [c["state"] for c in result["candidates"]]
        assert "dock" in candidate_states
        assert "formation" in candidate_states

    def test_negative_anchor_prunes(self, full_graph, empty_session):
        # Loading spinner disqualifies main_menu; no other state matches "Welcome, Commander"
        obs = {
            "text_content": "Welcome, Commander",
            "dom_elements": ["#main-menu-container", ".loading-spinner"],
        }
        result = locate(full_graph, empty_session, obs)
        # main_menu pruned by negative anchor → nothing else matches → unknown
        assert result["state"] == "unknown"

    def test_below_threshold_is_ambiguous(self, full_graph, empty_session):
        # dock has 2 anchors, threshold=0.7; matching only dom_element gives score=0.5 < 0.7
        obs = {"dom_elements": ["#dock-header"]}
        result = locate(full_graph, empty_session, obs)
        # Score 0.5 does not meet threshold 0.7 → ambiguous, not definitive
        assert "candidates" in result
        assert result["candidates"][0]["state"] == "dock"
        assert result["candidates"][0]["confidence"] == 0.5
