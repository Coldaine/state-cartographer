"""Tests for schema_validator.py — Graph Schema Validator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "plugin" / "scripts"))

from schema_validator import validate_graph


class TestValidateGraph:
    def test_valid_graph(self, full_graph):
        errors = validate_graph(full_graph)
        assert errors == []

    def test_missing_states(self):
        errors = validate_graph({"transitions": {}})
        assert any("states" in e for e in errors)

    def test_missing_transitions(self):
        errors = validate_graph({"states": {}})
        assert any("transitions" in e for e in errors)

    def test_not_dict(self):
        errors = validate_graph("bad")
        assert errors == ["Graph must be a JSON object"]

    def test_unknown_anchor_type(self):
        graph = {
            "states": {
                "s1": {"anchors": [{"type": "invalid_type", "cost": 1}]}
            },
            "transitions": {},
        }
        errors = validate_graph(graph)
        assert any("unknown type" in e for e in errors)

    def test_negative_cost(self):
        graph = {
            "states": {
                "s1": {"anchors": [{"type": "text_match", "pattern": "hi", "cost": -1}]}
            },
            "transitions": {},
        }
        errors = validate_graph(graph)
        assert any("non-negative" in e for e in errors)

    def test_invalid_confidence_threshold(self):
        graph = {
            "states": {
                "s1": {"confidence_threshold": 1.5}
            },
            "transitions": {},
        }
        errors = validate_graph(graph)
        assert any("confidence_threshold" in e for e in errors)

    def test_wait_state_missing_exit_signals(self):
        graph = {
            "states": {
                "s1": {"wait_state": True}
            },
            "transitions": {},
        }
        errors = validate_graph(graph)
        assert any("exit_signals" in e for e in errors)

    def test_transition_missing_source(self):
        graph = {
            "states": {"s1": {}, "s2": {}},
            "transitions": {"t1": {"dest": "s2"}},
        }
        errors = validate_graph(graph)
        assert any("source" in e for e in errors)

    def test_transition_bad_dest(self):
        graph = {
            "states": {"s1": {}},
            "transitions": {"t1": {"source": "s1", "dest": "nonexistent"}},
        }
        errors = validate_graph(graph)
        assert any("not found" in e for e in errors)

    def test_invalid_method(self):
        graph = {
            "states": {"s1": {}, "s2": {}},
            "transitions": {
                "t1": {"source": "s1", "dest": "s2", "method": "magic"}
            },
        }
        errors = validate_graph(graph)
        assert any("unknown method" in e for e in errors)
