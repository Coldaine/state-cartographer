"""adb_bridge.py — ADB Bridge for MEMU/Android emulator interaction.

Wraps ADB subprocess calls to provide screenshot capture, tap, swipe, and
device enumeration for state graph integration with MEMU (Azur Lane) and
other Android emulators.

Usage (CLI):
  python adb_bridge.py devices
  python adb_bridge.py connect --serial 127.0.0.1:21503
  python adb_bridge.py screenshot --serial 127.0.0.1:21503 --output screen.png
  python adb_bridge.py tap --serial 127.0.0.1:21503 --x 500 --y 400
  python adb_bridge.py swipe --serial 127.0.0.1:21503 --x1 500 --y1 400 --x2 500 --y2 200
  python adb_bridge.py keyevent --serial 127.0.0.1:21503 --keycode 4

MEMU default ADB ports:
  127.0.0.1:21503  (most versions)
  127.0.0.1:21513  (some newer versions)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Known MEMU ADB TCP serials (newest first so that newer versions succeed first).
MEMU_SERIALS: list[str] = [
    "127.0.0.1:21503",
    "127.0.0.1:21513",
    "127.0.0.1:21523",
]
DEFAULT_SERIAL = "127.0.0.1:21503"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run an ADB command, raising RuntimeError when ADB binary is missing."""
    try:
        return subprocess.run(args, **kwargs)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ADB not found. Install Android SDK Platform-Tools and add to PATH.\n"
            "Download: https://developer.android.com/studio/releases/platform-tools"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def devices() -> list[dict[str, str]]:
    """Return connected ADB devices.

    Returns:
        List of dicts with keys ``serial`` and ``state``.
        ``state`` is typically ``'device'``, ``'offline'``, or ``'unauthorized'``.
    """
    result = _run(["adb", "devices"], capture_output=True, text=True, check=False)
    lines = result.stdout.strip().splitlines()
    out: list[dict[str, str]] = []
    for line in lines[1:]:  # skip "List of devices attached" header
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            out.append({"serial": parts[0], "state": parts[1]})
    return out


def connect(serial: str) -> bool:
    """Connect to a device over TCP.

    Args:
        serial: ADB TCP serial, e.g. ``'127.0.0.1:21503'``.

    Returns:
        ``True`` if ADB reports the device is connected.
    """
    result = _run(["adb", "connect", serial], capture_output=True, text=True, check=False)
    return "connected" in result.stdout.lower()


def screenshot(serial: str, output_path: Path | str | None = None) -> bytes:
    """Capture a screenshot from the device as PNG bytes.

    Uses ``adb exec-out screencap -p`` which bypasses the Windows
    CRLF line-ending mangling that ``adb shell screencap -p`` can produce.

    Args:
        serial: ADB device serial (e.g. ``'127.0.0.1:21503'``).
        output_path: Optional path to write the PNG.  When provided the bytes
            are written to disk and also returned.

    Returns:
        Raw PNG bytes.

    Raises:
        RuntimeError: If ADB is not on PATH, the device is unreachable, or the
            returned data is not a valid PNG.
    """
    result = _run(
        ["adb", "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Screenshot failed (returncode {result.returncode}): {stderr}")

    data: bytes = result.stdout
    if not data or not data.startswith(b"\x89PNG"):
        raise RuntimeError(
            f"Screenshot returned invalid PNG data ({len(data)} bytes). "
            "Device may be offline, not authorised, or adb-server out of sync. "
            f"Try: adb connect {serial}"
        )

    if output_path is not None:
        Path(output_path).write_bytes(data)

    return data


def tap(serial: str, x: int, y: int) -> None:
    """Send a tap (touch) event to the device.

    Args:
        serial: ADB device serial.
        x: X coordinate in device pixels (0 to width-1).
        y: Y coordinate in device pixels (0 to height-1).
    """
    _run(
        ["adb", "-s", serial, "shell", "input", "tap", str(x), str(y)],
        capture_output=True,
        check=True,
    )


def swipe(
    serial: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int = 300,
) -> None:
    """Send a swipe gesture to the device.

    Args:
        serial: ADB device serial.
        x1, y1: Start coordinates.
        x2, y2: End coordinates.
        duration_ms: Gesture duration in milliseconds (default 300).
    """
    _run(
        [
            "adb",
            "-s",
            serial,
            "shell",
            "input",
            "swipe",
            str(x1),
            str(y1),
            str(x2),
            str(y2),
            str(duration_ms),
        ],
        capture_output=True,
        check=True,
    )


def key_event(serial: str, keycode: int | str) -> None:
    """Send an Android key event.

    Common keycodes::

        3  = HOME
        4  = BACK
        26 = POWER
        82 = MENU

    Args:
        serial: ADB device serial.
        keycode: Numeric keycode (int) or symbolic name (str, e.g. ``'KEYCODE_BACK'``).
    """
    _run(
        ["adb", "-s", serial, "shell", "input", "keyevent", str(keycode)],
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description="ADB bridge — emulator control for State Cartographer")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- devices ---
    sub.add_parser("devices", help="List connected ADB devices")

    # --- connect ---
    p_connect = sub.add_parser("connect", help="Connect to a device by TCP serial")
    p_connect.add_argument(
        "--serial",
        default=DEFAULT_SERIAL,
        help=f"Device serial (default: {DEFAULT_SERIAL})",
    )

    # --- screenshot ---
    p_shot = sub.add_parser("screenshot", help="Capture a screenshot to a PNG file")
    p_shot.add_argument(
        "--serial",
        default=DEFAULT_SERIAL,
        help=f"Device serial (default: {DEFAULT_SERIAL})",
    )
    p_shot.add_argument(
        "--output",
        default="screenshot.png",
        help="Output PNG file path (default: screenshot.png)",
    )

    # --- tap ---
    p_tap = sub.add_parser("tap", help="Send a tap event")
    p_tap.add_argument("--serial", default=DEFAULT_SERIAL)
    p_tap.add_argument("--x", type=int, required=True, help="X coordinate")
    p_tap.add_argument("--y", type=int, required=True, help="Y coordinate")

    # --- swipe ---
    p_swipe = sub.add_parser("swipe", help="Send a swipe gesture")
    p_swipe.add_argument("--serial", default=DEFAULT_SERIAL)
    p_swipe.add_argument("--x1", type=int, required=True, help="Start X")
    p_swipe.add_argument("--y1", type=int, required=True, help="Start Y")
    p_swipe.add_argument("--x2", type=int, required=True, help="End X")
    p_swipe.add_argument("--y2", type=int, required=True, help="End Y")
    p_swipe.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Gesture duration in ms (default: 300)",
    )

    # --- keyevent ---
    p_key = sub.add_parser("keyevent", help="Send a key event")
    p_key.add_argument("--serial", default=DEFAULT_SERIAL)
    p_key.add_argument(
        "--keycode",
        required=True,
        help="Keycode integer (4=BACK, 3=HOME) or name (KEYCODE_BACK)",
    )

    args = parser.parse_args()

    try:
        if args.command == "devices":
            devs = devices()
            if not devs:
                print("No devices connected.")
                print(f"For MEMU, try: adb connect {DEFAULT_SERIAL}")
            else:
                for d in devs:
                    print(f"  {d['serial']}\t{d['state']}")

        elif args.command == "connect":
            ok = connect(args.serial)
            if ok:
                print(f"Connected: {args.serial}")
            else:
                print(f"Failed to connect: {args.serial}", file=sys.stderr)
                return 1

        elif args.command == "screenshot":
            data = screenshot(args.serial, args.output)
            print(f"Screenshot saved: {args.output} ({len(data):,} bytes)")

        elif args.command == "tap":
            tap(args.serial, args.x, args.y)
            print(f"Tapped ({args.x}, {args.y})")

        elif args.command == "swipe":
            swipe(args.serial, args.x1, args.y1, args.x2, args.y2, args.duration)
            print(f"Swiped ({args.x1},{args.y1}) → ({args.x2},{args.y2})")

        elif args.command == "keyevent":
            key_event(args.serial, args.keycode)
            print(f"Key event sent: {args.keycode}")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
