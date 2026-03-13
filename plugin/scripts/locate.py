"""
locate.py — Passive State Classifier

Determines the current state of an external system by comparing observations
against a state graph's annotated anchors, using session history to constrain
candidates.

Input:
  - State graph definition (JSON with observation anchors)
  - Current session history (sequence of confirmed states + transitions)
  - Current observations (available signals: screenshot paths, pixel values, text matches)

Output:
  - Definitive state ID with confidence, OR
  - Candidate set with ranked disambiguation probes

Usage:
  python locate.py --graph graph.json --session session.json --observations obs.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load and return a JSON file."""
    with open(path) as f:
        return json.load(f)


def evaluate_anchors(
    state_id: str,
    anchors: list[dict[str, Any]],
    observations: dict[str, Any],
) -> float:
    """Evaluate observation anchors for a state and return confidence score.

    Anchors are evaluated in cost order (cheapest first). Each matching anchor
    increases confidence. Negative anchors immediately disqualify.
    """
    if not anchors:
        return 0.0

    sorted_anchors = sorted(anchors, key=lambda a: a.get("cost", 10))
    matches = 0
    total = len(sorted_anchors)

    for anchor in sorted_anchors:
        anchor_type = anchor.get("type", "")
        if anchor_type == "text_match":
            pattern = anchor.get("pattern", "")
            if observations.get("text_content") and pattern in observations["text_content"]:
                matches += 1
        elif anchor_type == "dom_element":
            selector = anchor.get("selector", "")
            present_elements = observations.get("dom_elements", [])
            if selector in present_elements:
                matches += 1
        elif anchor_type == "pixel_color":
            expected = tuple(anchor.get("expected_rgb", []))
            x, y = anchor.get("x", 0), anchor.get("y", 0)
            pixel_data = observations.get("pixels", {})
            actual = pixel_data.get(f"{x},{y}")
            if actual and tuple(actual) == expected:
                matches += 1
        elif anchor_type == "screenshot_region":
            # Perceptual hash comparison - requires imagehash
            matches += 0  # placeholder until imagehash integration

    return matches / total if total > 0 else 0.0


def check_negative_anchors(
    state_id: str,
    negative_anchors: list[dict[str, Any]],
    observations: dict[str, Any],
) -> bool:
    """Return True if any negative anchor matches (state is disqualified)."""
    for anchor in negative_anchors:
        anchor_type = anchor.get("type", "")
        if anchor_type == "dom_element":
            selector = anchor.get("selector", "")
            if selector in observations.get("dom_elements", []):
                return True
        elif anchor_type == "text_match":
            pattern = anchor.get("pattern", "")
            if observations.get("text_content") and pattern in observations["text_content"]:
                return True
    return False


def constrain_by_session(
    graph: dict[str, Any],
    session: dict[str, Any],
) -> list[str] | None:
    """Use session history to constrain candidate states.

    If the last confirmed state and transition are known, return only
    the states reachable via that transition. Returns None if no constraint.
    """
    history = session.get("history", [])
    if not history:
        return None

    last_entry = history[-1]
    if last_entry.get("type") == "transition":
        # Look up what states this transition can reach
        transitions = graph.get("transitions", {})
        transition_id = last_entry.get("transition_id", "")
        if transition_id in transitions:
            dest = transitions[transition_id].get("dest")
            if dest:
                return [dest] if isinstance(dest, str) else dest
    elif last_entry.get("type") == "confirmed_state":
        return [last_entry.get("state_id")]

    return None


def locate(
    graph: dict[str, Any],
    session: dict[str, Any],
    observations: dict[str, Any],
) -> dict[str, Any]:
    """Main locate function. Returns state classification result."""
    states = graph.get("states", {})
    session_constraint = constrain_by_session(graph, session)

    candidates = []
    for state_id, state_def in states.items():
        # Apply session constraint
        if session_constraint and state_id not in session_constraint:
            continue

        # Check negative anchors first
        negative_anchors = state_def.get("negative_anchors", [])
        if check_negative_anchors(state_id, negative_anchors, observations):
            continue

        # Evaluate positive anchors
        anchors = state_def.get("anchors", [])
        confidence = evaluate_anchors(state_id, anchors, observations)

        threshold = state_def.get("confidence_threshold", 0.7)
        candidates.append({
            "state": state_id,
            "confidence": confidence,
            "threshold": threshold,
        })

    if not candidates:
        return {
            "state": "unknown",
            "confidence": 0.0,
            "escalation": "vision_review",
            "message": "No matching state found. Observations match nothing in the graph.",
        }

    # Sort by confidence descending
    candidates.sort(key=lambda c: c["confidence"], reverse=True)

    best = candidates[0]

    # If no candidate has any positive confidence, state is unknown
    if best["confidence"] <= 0.0:
        return {
            "state": "unknown",
            "confidence": 0.0,
            "escalation": "vision_review",
            "message": "No matching state found. Observations match nothing in the graph.",
        }

    if best["confidence"] >= best["threshold"] and (
        len(candidates) == 1 or best["confidence"] > candidates[1]["confidence"]
    ):
        return {"state": best["state"], "confidence": best["confidence"]}

    # Ambiguous — return candidates with disambiguation probes
    return {
        "candidates": [
            {"state": c["state"], "confidence": c["confidence"]}
            for c in candidates[:5]
        ],
        "disambiguation": _suggest_probes(candidates, states),
    }


def _suggest_probes(
    candidates: list[dict[str, Any]],
    states: dict[str, Any],
) -> list[dict[str, Any]]:
    """Suggest probing actions to disambiguate between candidates."""
    probes = []
    top_candidates = [c["state"] for c in candidates[:3]]

    for state_id in top_candidates:
        state_def = states.get(state_id, {})
        for anchor in state_def.get("anchors", []):
            if anchor.get("type") == "dom_element":
                probes.append({
                    "action": "check_dom_element",
                    "selector": anchor.get("selector"),
                    "resolves": state_id,
                    "cost": anchor.get("cost", 5),
                })
            elif anchor.get("type") == "text_match":
                probes.append({
                    "action": "check_text",
                    "pattern": anchor.get("pattern"),
                    "resolves": state_id,
                    "cost": anchor.get("cost", 5),
                })

    probes.append({
        "action": "press_back",
        "observe": "response",
        "cost": 10,
    })

    probes.sort(key=lambda p: p.get("cost", 99))
    return probes


def main():
    parser = argparse.ArgumentParser(description="Passive state classifier")
    parser.add_argument("--graph", required=True, help="Path to graph JSON")
    parser.add_argument("--session", required=True, help="Path to session JSON")
    parser.add_argument("--observations", required=True, help="Path to observations JSON")
    args = parser.parse_args()

    graph = load_json(Path(args.graph))
    session = load_json(Path(args.session))
    observations = load_json(Path(args.observations))

    result = locate(graph, session, observations)
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
