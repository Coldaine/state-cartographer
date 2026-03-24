"""Executor — runs a task's action sequence against a live or mock system.

[!] STATUS: MVP PLACEHOLDER PROTOTYPE
This file is currently a structural placeholder for Layer 3 (Task Execution).
It naively executes static JSON step sequences (open-loop macros) and lacks
the dynamic vision capabilities (OCR, template matching) and complex control
flow (while-loops, dynamic scrolling) required for actual autonomous gameplay.
It proves the architectural shape, but is not yet capable of real domain logic.

The executor takes a task definition and steps through its action sequence.Each action is dispatched to the appropriate tool (navigate → pathfind + adb,
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
import socket
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
DEFAULT_SERIAL = "127.0.0.1:21513"  # MEmu Index 1 (32.87 GB) — the only supported instance


def _import_pilot_bridge_symbols() -> tuple[type[Any], int, int]:
    """Import PilotBridge symbols whether executor runs as module or script."""
    try:
        from scripts.pilot_bridge import LOCAL_ATX_PORT, LOCAL_DROIDCAST_PORT, PilotBridge
    except ImportError:
        from pilot_bridge import LOCAL_ATX_PORT, LOCAL_DROIDCAST_PORT, PilotBridge

    return PilotBridge, LOCAL_ATX_PORT, LOCAL_DROIDCAST_PORT


def load_json(path: Path) -> dict[str, Any]:
    """Load and return a JSON file as a dict."""
    with open(path) as f:
        return json.load(f)


# --- Backend interface ---
# The executor needs these capabilities from the runtime environment.
# Each is a callable. Tests inject mocks; live execution injects real ADB/etc.

BackendFn = Callable[..., Any]


def default_backend(serial: str = DEFAULT_SERIAL) -> dict[str, BackendFn]:
    """Return a backend dict with real implementations.

    This wires up to the actual scripts in this repo:
    - navigate: pathfind.py + adb_bridge.py
    - tap: adb_bridge.py tap
    - locate: locate.py
    - session_confirm: session.py confirm
    - sleep: time.sleep
    """

    def navigate(graph: dict[str, Any], current: str | None, target: str, **kw: Any) -> dict[str, Any]:
        kw.setdefault("serial", serial)
        return _navigate_real(graph=graph, current=current, target=target, **kw)

    def tap(coords: tuple[int, int], **kw: Any) -> dict[str, Any]:
        kw.setdefault("serial", serial)
        return _tap_real(coords=coords, **kw)

    def swipe(start: tuple[int, int], end: tuple[int, int], duration: int = 300, **kw: Any) -> dict[str, Any]:
        kw.setdefault("serial", serial)
        return _swipe_real(start=start, end=end, duration=duration, **kw)

    def locate(graph: dict[str, Any], **kw: Any) -> dict[str, Any]:
        kw.setdefault("serial", serial)
        return _locate_real(graph=graph, **kw)

    return {
        "navigate": navigate,
        "tap": tap,
        "swipe": swipe,
        "locate": locate,
        "session_confirm": _session_confirm_real,
        "sleep": time.sleep,
    }


def mock_backend() -> dict[str, BackendFn]:
    # TEST-ONLY: returns no-op stubs for all backend operations.
    # Nothing here touches the device.  Import and call only from tests.
    # In live execution, use build_backend("pilot") instead.
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


def pilot_backend(serial: str = DEFAULT_SERIAL) -> dict[str, BackendFn]:
    """Return a backend dict using PilotBridge (DroidCast) for MEmu interaction.

    This wires up to the PilotBridge class:
    - navigate: pathfind.py + pilot_bridge
    - tap: pilot_bridge.tap
    - swipe: pilot_bridge.swipe
    - locate: pilot_bridge.screenshot + locate.py
    - session_confirm: session.py confirm
    - sleep: time.sleep
    """
    PilotBridge, _, _ = _import_pilot_bridge_symbols()

    # Create a single PilotBridge instance to reuse
    bridge = PilotBridge(serial=serial)

    def _navigate_pilot(
        graph: dict[str, Any],
        current: str | None,
        target: str,
        **_kw: Any,
    ) -> dict[str, Any]:
        """Navigate from current to target using pathfind + pilot bridge."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from pathfind import pathfind

        if current is None:
            return {"success": False, "error": "Current state unknown"}

        result = pathfind(graph, current, target)
        if "error" in result:
            return {"success": False, "error": result["error"]}

        # Execute each step in the path
        route = result.get("route", [])
        for step in route:
            action = step.get("action", {})
            if action.get("type") == "adb_tap":
                coords = action.get("coords")
                if coords is None and "x" in action and "y" in action:
                    coords = [action["x"], action["y"]]
                if coords:
                    bridge.tap(coords[0], coords[1])
                    time.sleep(action.get("wait_after", 1.0))

        # Verify arrival
        loc_result = _locate_pilot(graph=graph, serial=serial)
        arrived_state = loc_result.get("state")
        if arrived_state != target:
            return {
                "success": False,
                "error": f"Navigation ended at '{arrived_state}' instead of '{target}'",
                "locate_result": loc_result,
            }

        return {"success": True, "state": target}

    def _tap_pilot(coords: tuple[int, int], **_kw: Any) -> dict[str, Any]:
        """Execute a tap using PilotBridge."""
        bridge.tap(coords[0], coords[1])
        return {"success": True}

    def _swipe_pilot(
        start: tuple[int, int],
        end: tuple[int, int],
        duration: int = 300,
        **_kw: Any,
    ) -> dict[str, Any]:
        """Execute a swipe using PilotBridge."""
        bridge.swipe(start[0], start[1], end[0], end[1], duration)
        return {"success": True}

    def _locate_pilot(graph: dict[str, Any], **_kw: Any) -> dict[str, Any]:
        """Locate using PilotBridge screenshot."""
        import contextlib
        import sys
        import tempfile
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from locate import locate
        from observe import build_observations, extract_pixel_coords

        # Extract pixel coordinates from graph
        pixel_coords = extract_pixel_coords(graph)

        # Capture screenshot using PilotBridge
        try:
            img = bridge.screenshot()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                screenshot_path = Path(tmp.name)
                img.save(screenshot_path)

            try:
                obs = build_observations(screenshot_path, pixel_coords)
                return locate(graph, {}, obs)
            finally:
                with contextlib.suppress(OSError):
                    screenshot_path.unlink()
        except Exception as e:
            return {"state": "unknown", "confidence": 0.0, "error": str(e)}

    def _session_confirm_pilot(state: str, session: dict[str, Any], **_kw: Any) -> dict[str, Any]:
        """Confirm state in the session."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from session import confirm_state

        return confirm_state(session, state)

    def _sleep_pilot(seconds: float) -> None:
        """Sleep."""
        time.sleep(seconds)

    def _handle_startup_popups_pilot(**_kw: Any) -> dict[str, Any]:
        """Execute one round of startup popup dismissal via PilotBridge."""
        bridge.handle_startup_popups()
        return {"success": True}

    return {
        "navigate": _navigate_pilot,
        "tap": _tap_pilot,
        "swipe": _swipe_pilot,
        "locate": _locate_pilot,
        "session_confirm": _session_confirm_pilot,
        "sleep": _sleep_pilot,
        "handle_startup_popups": _handle_startup_popups_pilot,
    }


def ldplayer_backend(serial: str = "127.0.0.1:5555", ldplayer_folder: str | None = None) -> dict[str, BackendFn]:
    """Return a backend dict using LDPlayerBridge (ldopengl64.dll) for LDPlayer interaction.

    Uses LDPlayer's native SDK for screenshots - much faster than DroidCast restart cycle.
    """
    from pilot_bridge import LDPlayerBridge

    bridge = LDPlayerBridge(serial=serial, ldplayer_folder=ldplayer_folder or "")

    def _navigate_ldplayer(
        graph: dict[str, Any],
        current: str | None,
        target: str,
        **_kw: Any,
    ) -> dict[str, Any]:
        """Navigate using pathfind + LDPlayer bridge."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from pathfind import pathfind

        if current is None:
            return {"success": False, "error": "Current state unknown"}

        result = pathfind(graph, current, target)
        if "error" in result:
            return {"success": False, "error": result["error"]}

        # Execute each step in the path
        route = result.get("route", [])
        for step in route:
            action = step.get("action", {})
            if action.get("type") == "adb_tap":
                coords = action.get("coords")
                if coords is None and "x" in action and "y" in action:
                    coords = [action["x"], action["y"]]
                if coords:
                    bridge.tap(coords[0], coords[1])
                    time.sleep(action.get("wait_after", 1.0))

        # Verify arrival
        loc_result = _locate_ldplayer(graph=graph)
        arrived_state = loc_result.get("state")
        if arrived_state != target:
            return {
                "success": False,
                "error": f"Navigation ended at '{arrived_state}' instead of '{target}'",
                "locate_result": loc_result,
            }

        return {"success": True, "state": target}

    def _tap_ldplayer(coords: tuple[int, int], **_kw: Any) -> dict[str, Any]:
        bridge.tap(coords[0], coords[1])
        return {"success": True}

    def _swipe_ldplayer(
        start: tuple[int, int],
        end: tuple[int, int],
        duration: int = 300,
        **_kw: Any,
    ) -> dict[str, Any]:
        bridge.swipe(start[0], start[1], end[0], end[1], duration)
        return {"success": True}

    def _locate_ldplayer(graph: dict[str, Any], **_kw: Any) -> dict[str, Any]:
        """Locate using LDPlayerBridge screenshot."""
        import contextlib
        import sys
        import tempfile
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from locate import locate
        from observe import build_observations, extract_pixel_coords

        pixel_coords = extract_pixel_coords(graph)

        try:
            img = bridge.screenshot()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                screenshot_path = Path(tmp.name)
                img.save(screenshot_path)

            try:
                obs = build_observations(screenshot_path, pixel_coords)
                return locate(graph, {}, obs)
            finally:
                with contextlib.suppress(OSError):
                    screenshot_path.unlink()
        except Exception as e:
            return {"state": "unknown", "confidence": 0.0, "error": str(e)}

    def _session_confirm_ldplayer(state: str, session: dict[str, Any], **_kw: Any) -> dict[str, Any]:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))
        from session import confirm_state

        return confirm_state(session, state)

    def _sleep_ldplayer(seconds: float) -> None:
        time.sleep(seconds)

    return {
        "navigate": _navigate_ldplayer,
        "tap": _tap_ldplayer,
        "swipe": _swipe_ldplayer,
        "locate": _locate_ldplayer,
        "session_confirm": _session_confirm_ldplayer,
        "sleep": _sleep_ldplayer,
    }


def build_backend(
    backend_name: str, serial: str = DEFAULT_SERIAL, config: dict[str, Any] | None = None
) -> dict[str, BackendFn]:
    """Build a backend by name.

    Canonical live backend for MEmu/Azur Lane is ``pilot``.
    ``ldplayer`` is for LDPlayer using native ldopengl64.dll (fastest).
    ``adb`` remains available for non-MEmu or debug scenarios but returns
    BLANK FRAMES on MEmu with DirectX rendering — do not use it for live work.
    ``mock`` is a TEST-ONLY no-op backend; never use it in live execution.

    Args:
        backend_name: Backend type ('pilot', 'ldplayer', 'adb', 'mock')
        serial: ADB serial for the device
        config: Optional config dict with emulator-specific settings (e.g., ldplayer_folder)
    """
    config = config or {}

    if backend_name == "mock":
        return mock_backend()
    if backend_name == "pilot":
        return pilot_backend(serial=serial)
    if backend_name == "ldplayer":
        return ldplayer_backend(
            serial=config.get("adb_serial", serial),
            ldplayer_folder=config.get("paths", {}).get("ldplayer_folder") if config else None,
        )
    if backend_name == "adb":
        logger.warning(
            "'adb' backend uses raw 'adb screencap' which returns BLANK FRAMES on MEmu "
            "with DirectX rendering. Use backend='pilot' for live execution on MEmu."
        )
        return default_backend(serial=serial)
    raise ValueError(f"Unknown backend: {backend_name}")


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def _run_text(*args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def live_preflight(serial: str = DEFAULT_SERIAL) -> dict[str, Any]:
    """Run explicit live preflight checks for the canonical PilotBridge path.

    This is intentionally not a background heartbeat. It is an explicit
    proof-of-readiness check at the single supported live entrypoint.
    A connection is considered ready only if transport, ATX, forwards,
    and screenshot observation are all proven.
    """
    PilotBridge, LOCAL_ATX_PORT, LOCAL_DROIDCAST_PORT = _import_pilot_bridge_symbols()

    report: dict[str, Any] = {
        "entrypoint": "scripts/executor.py",
        "backend": "pilot",
        "serial": serial,
        "alas_running": PilotBridge._alas_running(),
        "host_ports_before": {
            "atx": _port_open("127.0.0.1", LOCAL_ATX_PORT),
            "droidcast": _port_open("127.0.0.1", LOCAL_DROIDCAST_PORT),
            "alas": _port_open("127.0.0.1", 22267),
        },
    }

    adb_connect = _run_text("adb", "connect", serial)
    adb_state = _run_text("adb", "-s", serial, "get-state")
    focus = _run_text("adb", "-s", serial, "shell", "dumpsys", "window", "windows")
    report["adb_connect"] = (adb_connect.stdout or adb_connect.stderr).strip()
    report["adb_state"] = (adb_state.stdout or adb_state.stderr).strip()
    report["focus"] = [
        line.strip() for line in focus.stdout.splitlines() if "mCurrentFocus=" in line or "mFocusedApp=" in line
    ]

    if adb_state.returncode != 0 or report["adb_state"] != "device":
        report["success"] = False
        report["error"] = f"ADB transport not ready for {serial}: {report['adb_state']}"
        return report

    try:
        bridge = PilotBridge(serial=serial, record=False)
        bridge.connect()
        report["forwards_after"] = [
            {"serial": owner, "local": local, "remote": remote}
            for owner, local, remote in bridge._list_all_forwards()
            if owner == serial
        ]
        report["host_ports_after"] = {
            "atx": _port_open("127.0.0.1", LOCAL_ATX_PORT),
            "droidcast": _port_open("127.0.0.1", LOCAL_DROIDCAST_PORT),
            "alas": _port_open("127.0.0.1", 22267),
        }
        report["observation"] = {
            "ok": True,
            "method": "PilotBridge.connect() proof-of-observation",
        }
        report["success"] = True
        return report
    except Exception as exc:
        report["success"] = False
        report["error"] = str(exc)
        return report


def execute_task_by_id(
    task_id: str,
    tasks_path: Path,
    graph_path: Path,
    *,
    backend_name: str = "pilot",
    serial: str = DEFAULT_SERIAL,
    preflight: bool | None = None,
    session: dict[str, Any] | None = None,
    config_name: str | None = None,
) -> dict[str, Any]:
    """Canonical live/task entrypoint for this repo.

    For MEmu/Azur Lane, call this with ``backend_name='pilot'``.
    For LDPlayer, use ``config_name='ldplayer'`` to auto-load settings.
    """
    # Load config if specified
    config = {}
    if config_name:
        from emulator_config import load_config

        config = load_config(config_name)
        backend_name = config.get("backend", backend_name)
        serial = config.get("adb_serial", serial)

    manifest = load_json(tasks_path)
    graph = load_json(graph_path)
    session = session or {"current_state": None, "history": []}

    task_def = manifest.get("tasks", {}).get(task_id)
    if not task_def:
        return {"success": False, "error": f"Task '{task_id}' not found"}

    if preflight is None:
        preflight = backend_name == "pilot"

    preflight_report: dict[str, Any] | None = None
    if preflight and backend_name == "pilot":
        preflight_report = live_preflight(serial=serial)
        if not preflight_report.get("success"):
            return {
                "success": False,
                "error": "Live preflight failed",
                "preflight": preflight_report,
            }

    backend = build_backend(backend_name, serial=serial, config=config)
    result = execute_task(task_def, graph, session, backend)
    result["entrypoint"] = "scripts/executor.py"
    result["backend"] = backend_name
    result["serial"] = serial
    if config_name:
        result["config"] = config_name
    if preflight_report is not None:
        result["preflight"] = preflight_report
    return result


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

    # Step 0: Orient if the current state is unknown.
    if current_state is None:
        logger.info("Session state unknown; locating current state before execution")
        loc_result = backend["locate"](graph=graph)
        located_state = loc_result.get("state")
        if located_state and located_state != "unknown":
            session = backend["session_confirm"](state=located_state, session=session)
            current_state = located_state

        # If state is still unknown, try clearing Azur Lane startup popups.
        # These popups appear at game launch and block all navigation.
        # ALWAYS Confirm — never Cancel (Cancel exits the game).
        if (not current_state or current_state == "unknown") and "handle_startup_popups" in backend:
            logger.info("State unknown after locate; attempting startup popup dismissal")
            for popup_round in range(5):
                backend["handle_startup_popups"]()
                loc_result = backend["locate"](graph=graph)
                located_state = loc_result.get("state")
                if located_state and located_state != "unknown":
                    logger.info("State resolved to '%s' after popup round %d", located_state, popup_round + 1)
                    session = backend["session_confirm"](state=located_state, session=session)
                    current_state = located_state
                    break
            else:
                logger.warning("State still unknown after 5 popup dismissal rounds")

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
    parser.add_argument(
        "--config",
        metavar="NAME",
        help="Emulator config name (e.g., 'memu', 'ldplayer'). See configs/ directory.",
    )
    parser.add_argument(
        "--backend",
        choices=["pilot", "adb", "mock", "ldplayer"],
        default="pilot",
        help="Backend to use. 'pilot' is for MEmu, 'ldplayer' for LDPlayer.",
    )
    parser.add_argument("--serial", default=DEFAULT_SERIAL, help="ADB serial for live backends")
    parser.add_argument("--mock", action="store_true", help="Deprecated alias for --backend mock")
    parser.add_argument("--preflight", action="store_true", help="Force a live preflight before execution")
    parser.add_argument("--preflight-only", action="store_true", help="Run preflight and exit")

    args = parser.parse_args()

    # Load config if specified
    serial = args.serial
    backend_name = args.backend

    if args.config:
        from emulator_config import load_config

        config = load_config(args.config)
        backend_name = config.get("backend", backend_name)
        serial = config.get("adb_serial", serial)
        print(f"Loaded config '{args.config}': backend={backend_name}, serial={serial}")

    backend_name = "mock" if args.mock else backend_name
    if args.mock:
        import sys as _sys

        print(
            "WARNING: --mock is a deprecated alias for --backend mock. Use --backend mock explicitly.",
            file=_sys.stderr,
        )
    if backend_name == "mock":
        import sys as _sys

        print(
            "WARNING: Running with the 'mock' backend — no real device interactions occur. "
            "All actions are no-ops. Use --backend pilot for live execution.",
            file=_sys.stderr,
        )
    if backend_name == "adb":
        import sys as _sys

        print(
            "WARNING: The 'adb' backend uses raw 'adb screencap' which returns BLANK FRAMES "
            "on some emulators. Use --config for your emulator type.",
            file=_sys.stderr,
        )
    if args.preflight_only:
        if backend_name not in ("pilot", "ldplayer"):
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "--preflight-only is only supported for pilot and ldplayer backends",
                        "backend": backend_name,
                    },
                    indent=2,
                )
            )
            return
        print(json.dumps(live_preflight(serial=serial), indent=2, default=str))
        return

    result = execute_task_by_id(
        args.task,
        Path(args.tasks),
        Path(args.graph),
        backend_name=backend_name,
        serial=serial,
        preflight=args.preflight or backend_name in ("pilot", "ldplayer"),
        config_name=args.config,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
