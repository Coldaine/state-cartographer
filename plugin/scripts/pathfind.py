"""
pathfind.py — Weighted Route Planner

Computes the cheapest path between any two states in the graph using
transition cost annotations. Uses Dijkstra's algorithm over the state graph.

Usage:
  python pathfind.py --graph graph.json --from current_state --to target_state
  python pathfind.py --graph graph.json --from current_state --to target_state --avoid broken_state
  python pathfind.py --graph graph.json --from current_state --to target_state --prefer deterministic
"""
from __future__ import annotations

import argparse
import heapq
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def build_adjacency(
    graph: dict[str, Any],
    avoid: list[str] | None = None,
    prefer_deterministic: bool = False,
) -> dict[str, list[tuple[str, float, dict[str, Any]]]]:
    """Build adjacency list from graph transitions.

    Returns dict mapping state_id -> [(dest_state, cost, transition_def), ...]
    """
    avoid_set = set(avoid or [])
    transitions = graph.get("transitions", {})
    adj: dict[str, list[tuple[str, float, dict[str, Any]]]] = {}

    for trans_id, trans_def in transitions.items():
        source = trans_def.get("source")
        dest = trans_def.get("dest")
        if not source or not dest:
            continue
        if source in avoid_set or dest in avoid_set:
            continue

        cost = trans_def.get("cost", 10)

        # Bias toward deterministic transitions if requested
        if prefer_deterministic:
            method = trans_def.get("method", "unknown")
            if method == "deterministic":
                cost = max(1, cost * 0.5)
            elif method == "vision_required":
                cost = cost * 2.0

        if source not in adj:
            adj[source] = []
        adj[source].append((dest, cost, trans_def))

    return adj


def dijkstra(
    adj: dict[str, list[tuple[str, float, dict[str, Any]]]],
    start: str,
    end: str,
) -> tuple[list[dict[str, Any]], float] | None:
    """Dijkstra's shortest path. Returns (route, total_cost) or None."""
    if start == end:
        return [], 0.0

    dist: dict[str, float] = {start: 0.0}
    prev: dict[str, tuple[str, dict[str, Any]] | None] = {start: None}
    pq = [(0.0, start)]

    while pq:
        d, u = heapq.heappop(pq)
        if u == end:
            break
        if d > dist.get(u, float("inf")):
            continue
        for v, w, trans_def in adj.get(u, []):
            new_dist = d + w
            if new_dist < dist.get(v, float("inf")):
                dist[v] = new_dist
                prev[v] = (u, trans_def)
                heapq.heappush(pq, (new_dist, v))

    if end not in prev:
        return None

    # Reconstruct path
    route = []
    current = end
    while prev.get(current) is not None:
        from_state, trans_def = prev[current]
        route.append({
            "from": from_state,
            "to": current,
            "action": trans_def.get("action", {}),
            "method": trans_def.get("method", "unknown"),
            "cost": trans_def.get("cost", 10),
        })
        current = from_state

    route.reverse()
    return route, dist[end]


def pathfind(
    graph: dict[str, Any],
    start: str,
    end: str,
    avoid: list[str] | None = None,
    prefer_deterministic: bool = False,
) -> dict[str, Any]:
    """Find cheapest route between two states."""
    # Validate states exist
    states = graph.get("states", {})
    if start not in states:
        return {"error": f"Start state '{start}' not found in graph"}
    if end not in states:
        return {"error": f"End state '{end}' not found in graph"}

    if start == end:
        return {"route": [], "total_cost": 0.0, "message": "Already at target state"}

    adj = build_adjacency(graph, avoid=avoid, prefer_deterministic=prefer_deterministic)
    result = dijkstra(adj, start, end)

    if result is None:
        return {
            "error": f"No path from '{start}' to '{end}'",
            "avoided": avoid or [],
        }

    route, total_cost = result
    return {
        "route": route,
        "total_cost": total_cost,
        "hops": len(route),
        "deterministic_steps": sum(1 for r in route if r["method"] == "deterministic"),
        "vision_steps": sum(1 for r in route if r["method"] == "vision_required"),
    }


def main():
    parser = argparse.ArgumentParser(description="Weighted route planner")
    parser.add_argument("--graph", required=True, help="Path to graph JSON")
    parser.add_argument("--from", dest="from_state", required=True, help="Start state")
    parser.add_argument("--to", dest="to_state", required=True, help="Target state")
    parser.add_argument("--avoid", nargs="*", help="States to avoid")
    parser.add_argument("--prefer", choices=["deterministic"], help="Prefer deterministic transitions")
    args = parser.parse_args()

    graph = load_json(Path(args.graph))
    result = pathfind(
        graph,
        args.from_state,
        args.to_state,
        avoid=args.avoid,
        prefer_deterministic=args.prefer == "deterministic",
    )
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
