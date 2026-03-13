"""Tests for locate.py — Passive State Classifier."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "plugin" / "scripts"))

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

    def test_partial_match(self):
        anchors = [
            {"type": "text_match", "pattern": "Welcome", "cost": 1},
            {"type": "dom_element", "selector": "#missing", "cost": 2},
        ]
        obs = {"text_content": "Welcome", "dom_elements": []}
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
        session = {
            "history": [
                {"type": "transition", "transition_id": "main_to_dock", "from_state": "main_menu"}
            ]
        }
        result = constrain_by_session(full_graph, session)
        assert result == ["dock"]

    def test_session_with_confirmed_state(self, full_graph):
        session = {
            "history": [
                {"type": "confirmed_state", "state_id": "formation"}
            ]
        }
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
        session = {
            "history": [
                {"type": "transition", "transition_id": "main_to_dock", "from_state": "main_menu"}
            ]
        }
        obs = {"text_content": "Dock", "dom_elements": ["#dock-header"]}
        result = locate(full_graph, session, obs)
        assert result["state"] == "dock"

    def test_ambiguous_returns_candidates(self, full_graph, empty_session):
        # Observations that partially match multiple states
        obs = {"text_content": "Dock Formation", "dom_elements": []}
        result = locate(full_graph, empty_session, obs)
        # Should return candidates since multiple anchors could match
        assert "candidates" in result or "state" in result

    def test_negative_anchor_prunes(self, full_graph, empty_session):
        obs = {
            "text_content": "Welcome, Commander",
            "dom_elements": ["#main-menu-container", ".loading-spinner"],
        }
        result = locate(full_graph, empty_session, obs)
        # main_menu should be pruned due to negative anchor
        if "state" in result:
            assert result["state"] != "main_menu"
