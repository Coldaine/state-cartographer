"""Tests for session.py — Session State Manager."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from session import confirm_state, init_session, query_session, record_transition


class TestInitSession:
    def test_creates_valid_session(self):
        session = init_session("test-graph.json")
        assert session["graph_path"] == "test-graph.json"
        assert session["current_state"] is None
        assert session["history"] == []
        assert "created_at" in session


class TestConfirmState:
    def test_updates_current_state(self, empty_session):
        session = confirm_state(empty_session, "main_menu")
        assert session["current_state"] == "main_menu"
        assert len(session["history"]) == 1
        assert session["history"][0]["type"] == "confirmed_state"
        assert session["history"][0]["state_id"] == "main_menu"

    def test_appends_to_history(self, empty_session):
        session = confirm_state(empty_session, "main_menu")
        session = confirm_state(session, "dock")
        assert session["current_state"] == "dock"
        assert len(session["history"]) == 2


class TestRecordTransition:
    def test_records_transition(self, empty_session):
        session = confirm_state(empty_session, "main_menu")
        session = record_transition(session, "main_to_dock")
        assert session["current_state"] is None  # uncertain until confirmed
        assert len(session["history"]) == 2
        assert session["history"][-1]["type"] == "transition"
        assert session["history"][-1]["transition_id"] == "main_to_dock"
        assert session["history"][-1]["from_state"] == "main_menu"


class TestQuerySession:
    def test_empty_session(self, empty_session):
        result = query_session(empty_session)
        assert result["current_state"] is None
        assert result["total_confirmations"] == 0
        assert result["total_transitions"] == 0

    def test_mid_session(self, mid_session):
        result = query_session(mid_session)
        assert result["current_state"] == "dock"
        assert result["total_confirmations"] == 2
        assert result["total_transitions"] == 1
        assert "main_menu" in result["unique_states_visited"]
        assert "dock" in result["unique_states_visited"]
