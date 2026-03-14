"""
session.py — Session State Manager

Maintains the running record of confirmed states and transitions for the
current automation session. Used by locate.py to constrain candidates.

Usage:
  python session.py init --graph graph.json --output session.json
  python session.py confirm --session session.json --state main_menu
  python session.py transition --session session.json --event tap_dock
  python session.py query --session session.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def init_session(graph_path: str) -> dict[str, Any]:
    """Create a new empty session."""
    return {
        "graph_path": graph_path,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "current_state": None,
        "history": [],
    }


def confirm_state(session: dict[str, Any], state_id: str) -> dict[str, Any]:
    """Record a confirmed state in the session."""
    session["current_state"] = state_id
    session["history"].append(
        {
            "type": "confirmed_state",
            "state_id": state_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    return session


def record_transition(session: dict[str, Any], transition_id: str) -> dict[str, Any]:
    """Record a transition taken in the session."""
    session["history"].append(
        {
            "type": "transition",
            "transition_id": transition_id,
            "from_state": session.get("current_state"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    # Current state becomes uncertain until next confirm
    session["current_state"] = None
    return session


def query_session(session: dict[str, Any]) -> dict[str, Any]:
    """Return current session state and summary."""
    history = session.get("history", [])
    confirmed_states = [h["state_id"] for h in history if h["type"] == "confirmed_state"]
    transitions_taken = [h["transition_id"] for h in history if h["type"] == "transition"]

    return {
        "current_state": session.get("current_state"),
        "total_confirmations": len(confirmed_states),
        "total_transitions": len(transitions_taken),
        "unique_states_visited": list(set(confirmed_states)),
        "last_entry": history[-1] if history else None,
        "created_at": session.get("created_at"),
    }


def main():
    parser = argparse.ArgumentParser(description="Session state manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--graph", required=True)
    init_parser.add_argument("--output", required=True)

    confirm_parser = subparsers.add_parser("confirm")
    confirm_parser.add_argument("--session", required=True)
    confirm_parser.add_argument("--state", required=True)

    transition_parser = subparsers.add_parser("transition")
    transition_parser.add_argument("--session", required=True)
    transition_parser.add_argument("--event", required=True)

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--session", required=True)

    args = parser.parse_args()

    if args.command == "init":
        session = init_session(args.graph)
        save_json(Path(args.output), session)
        json.dump(session, sys.stdout, indent=2)
    elif args.command == "confirm":
        session = load_json(Path(args.session))
        session = confirm_state(session, args.state)
        save_json(Path(args.session), session)
        json.dump({"confirmed": args.state}, sys.stdout, indent=2)
    elif args.command == "transition":
        session = load_json(Path(args.session))
        session = record_transition(session, args.event)
        save_json(Path(args.session), session)
        json.dump({"transition": args.event}, sys.stdout, indent=2)
    elif args.command == "query":
        session = load_json(Path(args.session))
        result = query_session(session)
        json.dump(result, sys.stdout, indent=2)

    print()


if __name__ == "__main__":
    main()
