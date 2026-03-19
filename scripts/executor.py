"""Executor — runs a task's action sequence against a live or mock system.

The executor takes a task definition and steps through its action sequence.
Each action is dispatched to the appropriate tool (navigate → pathfind + adb,
tap → adb_bridge, wait → sleep, etc.).

Session tracking is automatic — every navigation and state change is recorded
without the agent needing to manually call session.py.

The executor is designed to be testable: all external dependencies (adb, sleep,
locate) are injected as a "backend" dict, so tests can supply mocks.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_json(path: Path) -> dict[str, Any]:
    """Load and return a JSON file as a dict."""
    with open(path) as f:
        return json.load(f)


# --- Backend interface ---
# The executor needs these capabilities from the runtime environment.
# Each is a callable. Tests inject mocks; live execution injects real ADB/etc.

BackendFn = Callable[..., Any]


def default_backend() -> dict[str, BackendFn]:
    """Return a backend dict with real implementations.

    This wires up to the actual scripts in this repo:
    - navigate: pathfind.py + adb_bridge.py
    - tap: adb_bridge.py tap
    - locate: locate.py
    - session_confirm: session.py confirm
    - sleep: time.sleep
    """
    return {
        "navigate": _navigate_real,
        "tap": _tap_real,
        "swipe": _swipe_real,
        "locate": _locate_real,
        "session_confirm": _session_confirm_real,
        "sleep": time.sleep,
    }


def mock_backend() -> dict[str, BackendFn]:
    """Return a backend dict with no-op mocks for testing."""
    log: list[dict[str, Any]] = []

    def mock_navigate(graph: dict, current: str | None, target: str, **_kw: Any) -> dict[str, Any]:
        log.append({"action": "navigate", "from": current, "to": target})
        return {"success": True, "state": target}

    def mock_tap(coords: tuple[int, int], **_kw: Any) -> dict[str, Any]:
        log.append({"action": "tap", "coords": coords})
        return {"success": True}

    def mock_swipe(start: tuple[int, int], end: tuple[int, int], **_kw: Any) -> dict[str, Any]:
        log.append({"action": "swipe", "start": start, "end": end})
        return {"success": True}

    def mock_locate(graph: dict, **_kw: Any) -> dict[str, Any]:
        log.append({"action": "locate"})
        return {"state": "unknown", "confidence": 0.0}

    def mock_confirm(state: str, session: dict, **_kw: Any) -> dict[str, Any]:
        log.append({"action": "session_confirm", "state": state})
        session["current_state"] = state
        return session

    def mock_sleep(seconds: float) -> None:
        log.append({"action": "sleep", "seconds": seconds})

    backend = {
        "navigate": mock_navigate,
        "tap": mock_tap,
        "swipe": mock_swipe,
        "locate": mock_locate,
        "session_confirm": mock_confirm,
        "sleep": mock_sleep,
    }
    # Expose log for test assertions (not part of the formal backend interface)
    backend["_log"] = log  # type: ignore
    return backend


def execute_task(
    task_def: dict[str, Any],
    graph: dict[str, Any],
    session: dict[str, Any],
    backend: dict[str, BackendFn] | None = None,
) -> dict[str, Any]:
    """Execute a task's full action sequence.

    Args:
        task_def: The task definition (from tasks.json)
        graph: The state graph (from graph.json)
        session: The current session state (from session.py)
        backend: Injectable backend functions (defaults to real implementations)

    Returns:
        Result dict with:
          - success: bool
          - session: updated session dict
          - actions_completed: int
          - error: str (if failed)
    """
    if backend is None:
        backend = default_backend()

    actions = task_def.get("actions", [])
    entry_state = task_def.get("entry_state")
    current_state = session.get("current_state")

    # Step 1: Navigate to entry state if needed
    if entry_state and current_state != entry_state:
        logger.info("Navigating to entry state: %s", entry_state)
        nav_result = backend["navigate"](
            graph=graph,
            current=current_state,
            target=entry_state,
        )
        if not nav_result.get("success"):
            return {
                "success": False,
                "session": session,
                "actions_completed": 0,
                "error": f"Failed to navigate to {entry_state}: {nav_result.get('error', 'unknown')}",
            }
        # Auto session tracking
        session = backend["session_confirm"](state=entry_state, session=session)
        current_state = entry_state

    # Step 2: Execute action sequence
    completed = 0
    for i, action in enumerate(actions):
        try:
            result = _execute_action(action, graph, session, current_state, backend)
            if not result.get("success", True):
                return {
                    "success": False,
                    "session": session,
                    "actions_completed": completed,
                    "error": f"Action {i} ({action.get('type', '?')}) failed: {result.get('error', 'unknown')}",
                }

            # Update state if the action changed it
            if "state" in result:
                current_state = result["state"]
                session = backend["session_confirm"](state=current_state, session=session)

            completed += 1

        except Exception as exc:
            logger.exception("Action %d failed with exception", i)
            return {
                "success": False,
                "session": session,
                "actions_completed": completed,
                "error": f"Action {i} raised {type(exc).__name__}: {exc}",
            }

    return {
        "success": True,
        "session": session,
        "actions_completed": completed,
    }


def _execute_action(
    action: dict[str, Any],
    graph: dict[str, Any],
    session: dict[str, Any],
    current_state: str | None,
    backend: dict[str, BackendFn],
) -> dict[str, Any]:
    """Dispatch a single action step."""
    atype = action.get("type")

    if atype == "navigate":
        target = action["target_state"]
        result = backend["navigate"](graph=graph, current=current_state, target=target)
        if result.get("success"):
            result["state"] = target
        return result

    if atype == "tap":
        coords = tuple(action["coords"])
        return backend["tap"](coords=coords)

    if atype == "swipe":
        start = tuple(action["start"])
        end = tuple(action["end"])
        duration = action.get("duration_ms", 300)
        return backend["swipe"](start=start, end=end, duration=duration)

    if atype == "wait":
        seconds = action.get("seconds", 1.0)
        backend["sleep"](seconds)
        return {"success": True}

    if atype == "wait_until":
        target_state = action.get("target_state")
        timeout = action.get("timeout_seconds", 30)
        poll_interval = action.get("poll_interval", 2.0)
        return _wait_until_state(graph, target_state, timeout, poll_interval, backend)

    if atype == "assert_state":
        expected = action["expected_state"]
        loc_result = backend["locate"](graph=graph)
        actual = loc_result.get("state")
        if actual == expected:
            return {"success": True, "state": actual}
        return {
            "success": False,
            "error": f"Expected state '{expected}', got '{actual}'",
        }

    if atype == "read_resource":
        # Resource reading is a placeholder — will be wired to OCR later
        return {"success": True}

    if atype == "conditional":
        # Conditional execution based on a condition check
        # For now, always execute the "then" branch
        then_actions = action.get("then", [])
        for sub_action in then_actions:
            result = _execute_action(sub_action, graph, session, current_state, backend)
            if not result.get("success", True):
                return result
        return {"success": True}

    if atype == "repeat":
        count = action.get("count", 1)
        body = action.get("body", [])
        for _ in range(count):
            for sub_action in body:
                result = _execute_action(sub_action, graph, session, current_state, backend)
                if not result.get("success", True):
                    return result
        return {"success": True}

    return {"success": False, "error": f"Unknown action type: {atype}"}


def _wait_until_state(
    graph: dict[str, Any],
    target_state: str | None,
    timeout: float,
    poll_interval: float,
    backend: dict[str, BackendFn],
) -> dict[str, Any]:
    """Poll locate() until we reach the target state or timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        loc_result = backend["locate"](graph=graph)
        actual = loc_result.get("state")
        if actual == target_state:
            return {"success": True, "state": actual}
        backend["sleep"](poll_interval)

    return {
        "success": False,
        "error": f"Timed out waiting for state '{target_state}' after {timeout}s",
    }


# --- Real backend implementations ---
# These call the actual scripts in this repo.


def _navigate_real(
    graph: dict[str, Any],
    current: str | None,
    target: str,
    **_kw: Any,
) -> dict[str, Any]:
    """Navigate from current to target using pathfind + adb."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from pathfind import pathfind

    if current is None:
        return {"success": False, "error": "Current state unknown"}

    result = pathfind(graph, current, target)
    if "error" in result:
        return {"success": False, "error": result["error"]}

    # Execute each step in the path
    route = result.get("route", [])
    serial = _kw.get("serial", "127.0.0.1:21513")
    for step in route:
        action = step.get("action", {})
        if action.get("type") == "adb_tap":
            coords = action.get("coords")
            if coords is None and "x" in action and "y" in action:
                coords = [action["x"], action["y"]]
            if coords:
                _tap_real(coords=tuple(coords), serial=serial)
                time.sleep(action.get("wait_after", 1.0))

    loc_result = _locate_real(graph=graph, serial=serial)
    arrived_state = loc_result.get("state")
    if arrived_state != target:
        return {
            "success": False,
            "error": f"Navigation ended at '{arrived_state}' instead of '{target}'",
            "locate_result": loc_result,
        }

    return {"success": True, "state": target}


def _tap_real(coords: tuple[int, int], **_kw: Any) -> dict[str, Any]:
    """Execute an ADB tap at the given coordinates."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from adb_bridge import tap

    # Get serial from kwargs or use default
    serial = _kw.get("serial", "127.0.0.1:21513")
    tap(serial, coords[0], coords[1])
    return {"success": True}


def _swipe_real(
    start: tuple[int, int],
    end: tuple[int, int],
    duration: int = 300,
    **_kw: Any,
) -> dict[str, Any]:
    """Execute an ADB swipe."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from adb_bridge import swipe

    # Get serial from kwargs or use default
    serial = _kw.get("serial", "127.0.0.1:21513")
    swipe(serial, start[0], start[1], end[0], end[1], duration)
    return {"success": True}


def _locate_real(graph: dict[str, Any], **_kw: Any) -> dict[str, Any]:
    """Call locate.py to determine current state."""
    import contextlib
    import sys
    import tempfile

    sys.path.insert(0, str(Path(__file__).parent))
    from adb_bridge import screenshot as adb_screenshot
    from locate import locate
    from observe import build_observations, extract_pixel_coords

    serial = _kw.get("serial", "127.0.0.1:21513")
    pixel_coords = extract_pixel_coords(graph)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        screenshot_path = Path(tmp.name)

    try:
        adb_screenshot(serial, screenshot_path)
        obs = build_observations(screenshot_path, pixel_coords)
        return locate(graph, {}, obs)
    finally:
        with contextlib.suppress(OSError):
            screenshot_path.unlink()


def _session_confirm_real(state: str, session: dict[str, Any], **_kw: Any) -> dict[str, Any]:
    """Confirm state in the session."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from session import confirm_state

    return confirm_state(session, state)


def main() -> None:
    """CLI entry point for executor — run a single task."""
    parser = argparse.ArgumentParser(description="Task executor — run a task against the system")
    parser.add_argument("--task", required=True, help="Task ID to execute")
    parser.add_argument("--tasks", required=True, help="Path to tasks.json")
    parser.add_argument("--graph", required=True, help="Path to graph.json")
    parser.add_argument("--mock", action="store_true", help="Use mock backend (no real ADB)")

    args = parser.parse_args()

    manifest = load_json(Path(args.tasks))
    graph = load_json(Path(args.graph))
    session: dict[str, Any] = {
        "current_state": None,
        "history": [],
    }

    task_def = manifest.get("tasks", {}).get(args.task)
    if not task_def:
        print(json.dumps({"error": f"Task '{args.task}' not found"}))
        return

    backend = mock_backend() if args.mock else default_backend()
    result = execute_task(task_def, graph, session, backend)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
