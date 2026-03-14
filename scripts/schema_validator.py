"""
schema_validator.py — Graph Schema Validator

Validates graph definitions against the extended state-cartographer schema.
Reports clear errors pointing to specific problems.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALID_ANCHOR_TYPES = {"text_match", "dom_element", "pixel_color", "screenshot_region"}
VALID_METHODS = {"deterministic", "vision_required", "unknown"}
VALID_HASH_ALGORITHMS = {"phash", "dhash", "ahash", "whash"}


def _validate_anchor(anchor: dict, label: str, errors: list[str]) -> None:
    """Validate a single anchor dict, appending errors to the list."""
    anchor_type = anchor.get("type")
    if anchor_type not in VALID_ANCHOR_TYPES:
        errors.append(f"{label}: unknown type '{anchor_type}'. Valid: {sorted(VALID_ANCHOR_TYPES)}")
    if "cost" in anchor:
        cost = anchor["cost"]
        if not isinstance(cost, (int, float)) or cost < 0:
            errors.append(f"{label}: cost must be a non-negative number")

    if anchor_type == "screenshot_region":
        if "hash" in anchor and "region" not in anchor:
            errors.append(f"{label}: screenshot_region with 'hash' must also have a 'region' dict")
        if "region" in anchor:
            region = anchor["region"]
            if not isinstance(region, dict):
                errors.append(f"{label}: 'region' must be an object with x, y, width, height")
            else:
                for field in ("x", "y", "width", "height"):
                    if field in region and not isinstance(region[field], (int, float)):
                        errors.append(f"{label}: region.{field} must be a number")
        if "hash_algorithm" in anchor and anchor["hash_algorithm"] not in VALID_HASH_ALGORITHMS:
            errors.append(
                f"{label}: hash_algorithm '{anchor['hash_algorithm']}' is invalid. "
                f"Valid: {sorted(VALID_HASH_ALGORITHMS)}"
            )
        if "threshold" in anchor:
            t = anchor["threshold"]
            if not isinstance(t, (int, float)) or t < 0:
                errors.append(f"{label}: threshold must be a non-negative number")


def validate_graph(graph: dict[str, Any]) -> list[str]:
    """Validate a graph definition. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    if not isinstance(graph, dict):
        return ["Graph must be a JSON object"]

    # Check required top-level keys
    if "states" not in graph:
        errors.append("Missing required key: 'states'")
    if "transitions" not in graph:
        errors.append("Missing required key: 'transitions'")

    states = graph.get("states", {})
    transitions = graph.get("transitions", {})

    if not isinstance(states, dict):
        errors.append("'states' must be an object")
        return errors
    if not isinstance(transitions, dict):
        errors.append("'transitions' must be an object")
        return errors

    state_ids = set(states.keys())

    # Validate each state
    for state_id, state_def in states.items():
        if not isinstance(state_def, dict):
            errors.append(f"State '{state_id}': must be an object")
            continue

        # Validate anchors
        for i, anchor in enumerate(state_def.get("anchors", [])):
            _validate_anchor(anchor, f"State '{state_id}' anchor [{i}]", errors)

        # Validate negative anchors
        for i, anchor in enumerate(state_def.get("negative_anchors", [])):
            anchor_type = anchor.get("type")
            if anchor_type not in VALID_ANCHOR_TYPES:
                errors.append(f"State '{state_id}' negative_anchor [{i}]: unknown type '{anchor_type}'")

        # Validate confidence threshold
        if "confidence_threshold" in state_def:
            ct = state_def["confidence_threshold"]
            if not isinstance(ct, (int, float)) or ct < 0 or ct > 1:
                errors.append(f"State '{state_id}': confidence_threshold must be between 0 and 1")

        # Validate wait state annotations
        if state_def.get("wait_state") and not state_def.get("exit_signals"):
            errors.append(f"State '{state_id}': wait_state=true but no exit_signals defined")

    # Validate each transition
    for trans_id, trans_def in transitions.items():
        if not isinstance(trans_def, dict):
            errors.append(f"Transition '{trans_id}': must be an object")
            continue

        source = trans_def.get("source")
        dest = trans_def.get("dest")

        if not source:
            errors.append(f"Transition '{trans_id}': missing 'source'")
        elif source not in state_ids:
            errors.append(f"Transition '{trans_id}': source '{source}' not found in states")

        if not dest:
            errors.append(f"Transition '{trans_id}': missing 'dest'")
        elif dest not in state_ids:
            errors.append(f"Transition '{trans_id}': dest '{dest}' not found in states")

        if "cost" in trans_def:
            cost = trans_def["cost"]
            if not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"Transition '{trans_id}': cost must be non-negative number")

        if "method" in trans_def:
            method = trans_def["method"]
            if method not in VALID_METHODS:
                errors.append(f"Transition '{trans_id}': unknown method '{method}'. Valid: {sorted(VALID_METHODS)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a graph definition")
    parser.add_argument("graph", help="Path to graph JSON file")
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

    errors = validate_graph(graph)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Valid: no errors found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
