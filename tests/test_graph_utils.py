"""Tests for graph_utils.py — Graph Inspection Utilities."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from graph_utils import (
    graph_summary,
    list_states,
    orphan_states,
    reachable_within,
    states_missing_anchors,
    transitions_from,
    transitions_to,
    wait_states,
)


class TestListStates:
    def test_returns_all_states(self, simple_linear_graph):
        result = list_states(simple_linear_graph)
        assert set(result) == {"a", "b", "c", "d"}

    def test_full_graph(self, full_graph):
        result = list_states(full_graph)
        assert "main_menu" in result
        assert "dock" in result
        assert len(result) == 7


class TestTransitionsFrom:
    def test_from_state(self, full_graph):
        result = transitions_from(full_graph, "main_menu")
        dests = [t["dest"] for t in result]
        assert "dock" in dests
        assert "formation" in dests
        assert "sortie_select" in dests

    def test_no_outbound(self, simple_linear_graph):
        result = transitions_from(simple_linear_graph, "d")
        assert result == []


class TestTransitionsTo:
    def test_to_state(self, full_graph):
        result = transitions_to(full_graph, "main_menu")
        sources = [t["source"] for t in result]
        assert "battle_result" in sources


class TestReachableWithin:
    def test_one_hop(self, full_graph):
        result = reachable_within(full_graph, "main_menu", 1)
        assert "dock" in result
        assert "formation" in result
        assert "sortie_select" in result
        assert "auto_battle" not in result

    def test_two_hops(self, full_graph):
        result = reachable_within(full_graph, "main_menu", 2)
        assert "auto_battle" in result  # main -> sortie -> auto_battle


class TestOrphanStates:
    def test_finds_orphans(self, simple_linear_graph):
        # In linear a->b->c->d, 'a' is initial so not orphan. All others have inbound.
        result = orphan_states(simple_linear_graph)
        assert result == []  # all have inbound or are initial


class TestStatesMissingAnchors:
    def test_simple_graph_all_missing(self, simple_linear_graph):
        result = states_missing_anchors(simple_linear_graph)
        assert set(result) == {"a", "b", "c", "d"}

    def test_full_graph_none_missing(self, full_graph):
        result = states_missing_anchors(full_graph)
        assert result == []


class TestWaitStates:
    def test_finds_wait_states(self, full_graph):
        result = wait_states(full_graph)
        assert "auto_battle" in result


class TestGraphSummary:
    def test_summary(self, full_graph):
        result = graph_summary(full_graph)
        assert result["total_states"] == 7
        assert result["total_transitions"] == 9
        assert result["states_with_anchors"] == 7
        assert result["states_missing_anchors"] == 0
        assert "auto_battle" in result["wait_states"]
