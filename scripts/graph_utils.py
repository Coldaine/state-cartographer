"""
graph_utils.py — Graph Inspection Utilities

Wraps state graph definitions for common queries agents need:
list states, valid transitions, reachable states, orphans, missing anchors, etc.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def list_states(graph: dict[str, Any]) -> list[str]:
    """Return all state IDs in the graph."""
    return list(graph.get("states", {}).keys())


def list_transitions(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all transitions with their IDs."""
    return [{"id": tid, **tdef} for tid, tdef in graph.get("transitions", {}).items()]


def transitions_from(graph: dict[str, Any], state_id: str) -> list[dict[str, Any]]:
    """Return all transitions available from a given state."""
    return [{"id": tid, **tdef} for tid, tdef in graph.get("transitions", {}).items() if tdef.get("source") == state_id]


def transitions_to(graph: dict[str, Any], state_id: str) -> list[dict[str, Any]]:
    """Return all transitions leading to a given state."""
    return [{"id": tid, **tdef} for tid, tdef in graph.get("transitions", {}).items() if tdef.get("dest") == state_id]


def reachable_within(graph: dict[str, Any], state_id: str, max_hops: int) -> set[str]:
    """Return all states reachable from state_id within N hops."""
    visited: set[str] = set()
    frontier = {state_id}

    for _ in range(max_hops):
        next_frontier: set[str] = set()
        for s in frontier:
            for t in transitions_from(graph, s):
                dest = t.get("dest")
                if dest and dest not in visited:
                    next_frontier.add(dest)
        visited.update(frontier)
        frontier = next_frontier

    visited.update(frontier)
    visited.discard(state_id)
    return visited


def orphan_states(graph: dict[str, Any]) -> list[str]:
    """Return states with no inbound transitions (except the initial state)."""
    states = set(graph.get("states", {}).keys())
    has_inbound = set()
    for tdef in graph.get("transitions", {}).values():
        dest = tdef.get("dest")
        if dest:
            has_inbound.add(dest)

    initial = graph.get("initial_state")
    orphans = states - has_inbound
    if initial:
        orphans.discard(initial)
    return sorted(orphans)


def states_missing_anchors(graph: dict[str, Any]) -> list[str]:
    """Return states that have no observation anchors defined."""
    return sorted(sid for sid, sdef in graph.get("states", {}).items() if not sdef.get("anchors"))


def transitions_missing_costs(graph: dict[str, Any]) -> list[str]:
    """Return transition IDs that have no cost annotation."""
    return sorted(tid for tid, tdef in graph.get("transitions", {}).items() if "cost" not in tdef)


def wait_states(graph: dict[str, Any]) -> list[str]:
    """Return states annotated as wait states."""
    return sorted(sid for sid, sdef in graph.get("states", {}).items() if sdef.get("wait_state"))


def graph_summary(graph: dict[str, Any]) -> dict[str, Any]:
    """Return a summary of graph completeness."""
    states = graph.get("states", {})
    transitions = graph.get("transitions", {})
    missing_anchors = states_missing_anchors(graph)
    missing_costs = transitions_missing_costs(graph)

    return {
        "total_states": len(states),
        "total_transitions": len(transitions),
        "states_with_anchors": len(states) - len(missing_anchors),
        "states_missing_anchors": len(missing_anchors),
        "transitions_with_costs": len(transitions) - len(missing_costs),
        "transitions_missing_costs": len(missing_costs),
        "orphan_states": orphan_states(graph),
        "wait_states": wait_states(graph),
        "deterministic_transitions": sum(1 for t in transitions.values() if t.get("method") == "deterministic"),
        "vision_transitions": sum(1 for t in transitions.values() if t.get("method") == "vision_required"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Graph inspection utilities")
    parser.add_argument("--graph", required=True, help="Path to graph JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary", help="Print graph summary")
    sub.add_parser("states", help="List all states")
    sub.add_parser("orphans", help="List orphan states")
    sub.add_parser("missing-anchors", help="List states missing anchors")
    args = parser.parse_args()

    try:
        with Path(args.graph).open(encoding="utf-8") as file_obj:
            graph = json.load(file_obj)
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.graph}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: Could not read {args.graph}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {args.graph}: {exc}", file=sys.stderr)
        return 2

    if args.command == "summary":
        json.dump(graph_summary(graph), sys.stdout, indent=2)
    elif args.command == "states":
        json.dump(list_states(graph), sys.stdout, indent=2)
    elif args.command == "orphans":
        json.dump(orphan_states(graph), sys.stdout, indent=2)
    elif args.command == "missing-anchors":
        json.dump(states_missing_anchors(graph), sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
