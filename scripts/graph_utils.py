"""
graph_utils.py — Graph Inspection Utilities

Wraps state graph definitions for common queries agents need:
list states, valid transitions, reachable states, orphans, missing anchors, etc.
"""

from __future__ import annotations

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

    return {
        "total_states": len(states),
        "total_transitions": len(transitions),
        "states_with_anchors": len(states) - len(states_missing_anchors(graph)),
        "states_missing_anchors": len(states_missing_anchors(graph)),
        "transitions_with_costs": len(transitions) - len(transitions_missing_costs(graph)),
        "transitions_missing_costs": len(transitions_missing_costs(graph)),
        "orphan_states": orphan_states(graph),
        "wait_states": wait_states(graph),
        "deterministic_transitions": sum(1 for t in transitions.values() if t.get("method") == "deterministic"),
        "vision_transitions": sum(1 for t in transitions.values() if t.get("method") == "vision_required"),
    }
