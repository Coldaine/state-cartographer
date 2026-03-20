"""pilot_bridge.py — Live piloting bridge for MEmu/Azur Lane.

Provides screenshot capture (via DroidCast), tap/swipe actions (via ADB),
and event recording (via execution_event_log). Designed to be imported by
the agent or run interactively.

DroidCast is the only reliable screenshot method for MEmu with DirectX
rendering.  The standard ``screencap -p`` and ascreencap both return blank
on MEmu because the game renders through the host GPU, bypassing the
Android display compositor.

**MEmu DroidCast quirk**: DroidCast only returns ONE valid frame per
startup on MEmu's DirectX renderer.  To work around this, each call to
``screenshot()`` performs a full restart cycle:
  kill → start (via ATX agent) → port-forward → wait → capture.
Each cycle takes ~3 seconds but reliably returns real content.

Usage (library):
    from scripts.pilot_bridge import PilotBridge
    bridge = PilotBridge()
    bridge.connect()
    img = bridge.screenshot()                      # PIL Image
    bridge.tap(640, 360)
    bridge.screenshot("data/screenshots/after.png") # saves + returns

Usage (CLI):
    python scripts/pilot_bridge.py screenshot --output screen.png
    python scripts/pilot_bridge.py tap --x 640 --y 360
    python scripts/pilot_bridge.py connect
"""

from __future__ import annotations

import argparse
import subprocess
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image

# ---------------------------------------------------------------------------
# Optional import: event logging
# ---------------------------------------------------------------------------
try:
    from scripts.execution_event_log import append_event, make_event
except ImportError:
    try:
        from execution_event_log import append_event, make_event
    except ImportError:
        append_event = None  # type: ignore[assignment]
        make_event = None  # type: ignore[assignment]


DEFAULT_SERIAL = "127.0.0.1:21513"
DROIDCAST_APK_LOCAL = Path("vendor/AzurLaneAutoScript/bin/DroidCast/DroidCast_raw-release-1.0.apk")
DROIDCAST_APK_REMOTE = "/data/local/tmp/DroidCast_raw.apk"
DROIDCAST_PORT_REMOTE = 53516
ATX_AGENT_PORT = 7912
EVENT_LOG_DIR = Path("data/events")
SCREENSHOT_DIR = Path("data/screenshots")


def _adb(*args: str, serial: str = DEFAULT_SERIAL) -> subprocess.CompletedProcess[bytes]:
    """Run an ADB command targeting *serial*."""
    cmd = ["adb", "-s", serial, *args]
    return subprocess.run(cmd, capture_output=True, timeout=30)


class PilotBridge:
    """Live bridge to the MEmu emulator for piloting Azur Lane.

    Uses the ATX agent (uiautomator2's on-device daemon on port 7912) to
    manage DroidCast lifecycle.  Because DroidCast on MEmu's DirectX
    renderer only returns one valid frame per startup, each ``screenshot()``
    call performs a full restart cycle (~3 s).
    """

    def __init__(
        self,
        serial: str = DEFAULT_SERIAL,
        *,
        record: bool = True,
        run_id: str | None = None,
        event_log_path: Path | None = None,
        screenshot_dir: Path | None = None,
    ):
        self.serial = serial
        self.record = record and (make_event is not None)
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.event_log_path = event_log_path or EVENT_LOG_DIR / f"{self.run_id}.ndjson"
        self.screenshot_dir = screenshot_dir or SCREENSHOT_DIR
        self._session: requests.Session = requests.Session()
        self._session.trust_env = False
        self._atx_port: int = 0
        self._screenshot_serial = 0
        self._connected = False

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Establish ADB connection, verify ATX agent, push DroidCast APK."""
        # 1. ADB connect
        _adb("connect", self.serial, serial=self.serial)
        result = _adb("devices", serial=self.serial)
        if self.serial.encode() not in result.stdout:
            raise RuntimeError(f"Device {self.serial} not found after connect")

        # 2. Push DroidCast APK (idempotent)
        apk = DROIDCAST_APK_LOCAL
        if not apk.exists():
            raise FileNotFoundError(f"DroidCast APK not found: {apk}")
        _adb("push", str(apk), DROIDCAST_APK_REMOTE, serial=self.serial)

        # 3. Forward ATX agent port only — never remove-all (would kill ALAS's DroidCast forward)
        _adb("forward", "--remove", "tcp:17912", serial=self.serial)
        _adb("forward", "tcp:17912", f"tcp:{ATX_AGENT_PORT}", serial=self.serial)
        # Only add DroidCast forward if not already present (ALAS may own it)
        fwd_result = _adb("forward", "--list", serial=self.serial)
        if f"tcp:{DROIDCAST_PORT_REMOTE}" not in fwd_result.stdout.decode(errors="replace"):
            _adb("forward", f"tcp:{DROIDCAST_PORT_REMOTE}", f"tcp:{DROIDCAST_PORT_REMOTE}", serial=self.serial)
        self._atx_port = 17912

        # 4. Verify ATX agent responds
        try:
            resp = self._session.get(f"http://127.0.0.1:{self._atx_port}/info", timeout=5)
            resp.raise_for_status()
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise RuntimeError(
                "ATX agent not responding on port 7912. Ensure uiautomator2 was initialized on this device."
            ) from exc

        # 5. Verify with a test screenshot
        img = self._restart_and_capture()
        if img is None:
            raise RuntimeError("DroidCast restart-and-capture failed during connect")

        self._connected = True
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        if self.record:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal: restart-per-screenshot cycle
    # ------------------------------------------------------------------

    @staticmethod
    def _alas_running() -> bool:
        """Return True if ALAS web server is listening on port 22267."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", 22267)) == 0

    def _restart_and_capture(self) -> np.ndarray | None:
        """Kill DroidCast, restart via ATX, capture ONE frame.

        If ALAS is running, skip the kill/restart cycle and read directly from
        ALAS's existing DroidCast forward (port 53516) to avoid disrupting it.

        Returns a BGR numpy array, or None on failure.
        """
        import contextlib

        dc_port = DROIDCAST_PORT_REMOTE
        dc_base = f"http://127.0.0.1:{dc_port}"

        # If ALAS owns DroidCast, read from its existing endpoint — no kill/restart.
        if self._alas_running():
            try:
                r = self._session.get(f"{dc_base}/preview", timeout=5)
                arr = np.frombuffer(r.content, np.uint8)
                bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if bgr is not None:
                    return bgr
            except requests.RequestException:
                pass
            return None

        atx_url = f"http://127.0.0.1:{self._atx_port}"

        # Kill existing DroidCast (ignore failures — process may not be running)
        with contextlib.suppress(requests.RequestException):
            self._session.post(
                f"{atx_url}/shell",
                data={"command": "pkill -f droidcast_raw", "timeout": "5"},
                timeout=10,
            )
        time.sleep(1)

        # Start DroidCast via ATX background shell
        resp = self._session.post(
            f"{atx_url}/shell/background",
            data={
                "command": (f"CLASSPATH={DROIDCAST_APK_REMOTE} app_process / ink.mol.droidcast_raw.Main > /dev/null"),
                "timeout": "10",
            },
            timeout=20,
        )
        resp.raise_for_status()

        # Use fixed DroidCast local port (already forwarded in connect())
        dc_port = DROIDCAST_PORT_REMOTE

        # Wait for DroidCast to come online
        dc_base = f"http://127.0.0.1:{dc_port}"
        for _ in range(20):
            try:
                r2 = self._session.get(f"{dc_base}/", timeout=2)
                if r2.status_code == 404:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.25)

        # Capture one frame
        try:
            r3 = self._session.get(f"{dc_base}/preview", timeout=5)
            arr = np.frombuffer(r3.content, np.uint8)
            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return bgr
        except requests.RequestException:
            return None

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, save_path: str | Path | None = None) -> Image.Image:
        """Capture a screenshot via DroidCast (restart-per-capture).

        Returns a PIL Image.  If *save_path* is given, the PNG is also
        written to disk.  When recording is enabled, every screenshot is
        auto-saved to ``screenshot_dir``.
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

        bgr = self._restart_and_capture()
        if bgr is None:
            raise RuntimeError("DroidCast restart-and-capture returned no image")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        # Auto-save when recording
        self._screenshot_serial += 1
        auto_path = self.screenshot_dir / f"{self.run_id}_{self._screenshot_serial:04d}.png"
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(save_path)
        if self.record:
            auto_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(auto_path)

        return img

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def tap(self, x: int, y: int, *, label: str = "") -> None:
        """Tap at (x, y) on the device screen."""
        t0 = time.monotonic()
        _adb("shell", "input", "tap", str(x), str(y), serial=self.serial)
        dur = int((time.monotonic() - t0) * 1000)

        if self.record and make_event and append_event:
            evt = make_event(
                run_id=self.run_id,
                serial=self.serial,
                event_type="execution",
                ok=True,
                semantic_action=label or f"tap({x},{y})",
                primitive_action="tap",
                coords=[x, y],
                duration_ms=dur,
            )
            append_event(self.event_log_path, evt)

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
        *,
        label: str = "",
    ) -> None:
        """Swipe from (x1,y1) to (x2,y2)."""
        t0 = time.monotonic()
        _adb(
            "shell",
            "input",
            "swipe",
            str(x1),
            str(y1),
            str(x2),
            str(y2),
            str(duration_ms),
            serial=self.serial,
        )
        dur = int((time.monotonic() - t0) * 1000)

        if self.record and make_event and append_event:
            evt = make_event(
                run_id=self.run_id,
                serial=self.serial,
                event_type="execution",
                ok=True,
                semantic_action=label or f"swipe({x1},{y1}→{x2},{y2})",
                primitive_action="swipe",
                gesture={"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
                duration_ms=dur,
            )
            append_event(self.event_log_path, evt)

    def back(self) -> None:
        """Press the Android BACK key."""
        _adb("shell", "input", "keyevent", "4", serial=self.serial)
        if self.record and make_event and append_event:
            evt = make_event(
                run_id=self.run_id,
                serial=self.serial,
                event_type="execution",
                ok=True,
                semantic_action="back_button",
                primitive_action="keyevent",
            )
            append_event(self.event_log_path, evt)

    def wait(self, seconds: float) -> None:
        """Sleep and record the wait."""
        time.sleep(seconds)

    # ------------------------------------------------------------------
    # Observation logging
    # ------------------------------------------------------------------

    def log_observation(
        self,
        *,
        state: str,
        notes: str = "",
        screen_path: str | None = None,
    ) -> None:
        """Record an observation event (state classification)."""
        if self.record and make_event and append_event:
            evt = make_event(
                run_id=self.run_id,
                serial=self.serial,
                event_type="observation",
                ok=True,
                state_after=state,
                screen_after=screen_path,
                notes=notes,
            )
            append_event(self.event_log_path, evt)

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Pilot bridge — MEmu/AL interaction")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("connect", help="Connect and verify DroidCast")

    p_shot = sub.add_parser("screenshot", help="Take a screenshot")
    p_shot.add_argument("--output", default="data/screenshots/pilot.png")

    p_tap = sub.add_parser("tap", help="Tap at coordinates")
    p_tap.add_argument("--x", type=int, required=True)
    p_tap.add_argument("--y", type=int, required=True)

    args = parser.parse_args()
    bridge = PilotBridge()

    if args.command == "connect":
        bridge.connect()
        print(f"Connected. Run ID: {bridge.run_id}")

    elif args.command == "screenshot":
        bridge.connect()
        img = bridge.screenshot(args.output)
        print(f"Screenshot saved: {args.output} ({img.size[0]}x{img.size[1]})")

    elif args.command == "tap":
        bridge.connect()
        bridge.tap(args.x, args.y)
        print(f"Tapped ({args.x}, {args.y})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
