"""Tests for pathfind.py — Weighted Route Planner."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pathfind import build_adjacency, pathfind


class TestPathfind:
    def test_linear_path(self, simple_linear_graph):
        result = pathfind(simple_linear_graph, "a", "d")
        assert "route" in result
        assert result["hops"] == 3
        assert result["total_cost"] == 3.0

    def test_same_state_noop(self, simple_linear_graph):
        result = pathfind(simple_linear_graph, "a", "a")
        assert result["route"] == []
        assert result["total_cost"] == 0.0

    def test_no_path(self, simple_linear_graph):
        # d has no outbound transitions in linear graph
        result = pathfind(simple_linear_graph, "d", "a")
        assert "error" in result

    def test_invalid_start_state(self, simple_linear_graph):
        result = pathfind(simple_linear_graph, "nonexistent", "a")
        assert "error" in result

    def test_invalid_end_state(self, simple_linear_graph):
        result = pathfind(simple_linear_graph, "a", "nonexistent")
        assert "error" in result

    def test_cheapest_path_branching(self, branching_graph):
        result = pathfind(branching_graph, "a", "d")
        # a->b->d costs 2, a->c->d costs 51. Should pick a->b->d
        assert result["total_cost"] == 2.0
        assert result["hops"] == 2

    def test_avoid_state(self, branching_graph):
        result = pathfind(branching_graph, "a", "d", avoid=["b"])
        # Must go through c now
        assert result["total_cost"] == 51.0
        route_states = [r["to"] for r in result["route"]]
        assert "b" not in route_states

    def test_prefer_deterministic(self):
        # Inline graph: vision route is cheaper nominally but more expensive when biased.
        # Without preference: vision_required (cost 4) wins over deterministic (cost 10).
        # With preference: vision doubles to 8, deterministic halves to 5 -> deterministic wins.
        graph = {
            "states": {"start": {"anchors": []}, "end": {"anchors": []}},
            "transitions": {
                "via_vision": {"source": "start", "dest": "end", "method": "vision_required", "cost": 4},
                "via_det": {"source": "start", "dest": "end", "method": "deterministic", "cost": 10},
            },
        }
        without = pathfind(graph, "start", "end", prefer_deterministic=False)
        with_pref = pathfind(graph, "start", "end", prefer_deterministic=True)

        assert without["route"][0]["method"] == "vision_required"  # cheaper without bias
        assert with_pref["route"][0]["method"] == "deterministic"  # wins after bias applied

    def test_counts_methods(self, full_graph):
        # main_menu → sortie_select (deterministic) → auto_battle (vision_required)
        result = pathfind(full_graph, "main_menu", "auto_battle")
        assert result["deterministic_steps"] == 1
        assert result["vision_steps"] == 1


class TestBuildAdjacency:
    def test_builds_from_graph(self, simple_linear_graph):
        adj = build_adjacency(simple_linear_graph)
        assert "a" in adj
        assert len(adj["a"]) == 1  # a -> b

    def test_avoids_states(self, branching_graph):
        adj = build_adjacency(branching_graph, avoid=["b"])
        # a should only have a->c, not a->b
        dests = [dest for dest, _, _ in adj.get("a", [])]
        assert "b" not in dests
