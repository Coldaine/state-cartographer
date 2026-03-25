"""Thin worker around the borrowed py-scrcpy-client environment.

This script is intended to run under the dedicated py-scrcpy-client venv,
not the main project interpreter.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import scrcpy
from PIL import Image


def _start_client(serial: str, max_fps: int = 5) -> scrcpy.Client:
    client = scrcpy.Client(device=serial, max_fps=max_fps, block_frame=True)
    client.start(threaded=True)

    deadline = time.time() + 10
    while time.time() < deadline:
        if client.last_frame is not None:
            return client
        time.sleep(0.1)

    client.stop()
    raise RuntimeError("scrcpy client connected but no frame arrived")


def _write_frame_png(frame, path: Path) -> tuple[int, int, int]:
    rgb = frame[:, :, ::-1]
    image = Image.fromarray(rgb)
    image.save(path, format="PNG")
    return path.stat().st_size, frame.shape[1], frame.shape[0]


def _cmd_connect(args: argparse.Namespace) -> int:
    client = _start_client(args.serial, max_fps=args.max_fps)
    try:
        payload = {
            "connected": True,
            "serial": args.serial,
            "resolution": list(client.resolution or (0, 0)),
        }
        print(json.dumps(payload))
        return 0
    finally:
        client.stop()


def _cmd_capture(args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    client = _start_client(args.serial, max_fps=args.max_fps)
    try:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        size, width, height = _write_frame_png(client.last_frame, output)
        payload = {
            "path": str(output),
            "bytes": size,
            "width": width,
            "height": height,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        print(json.dumps(payload))
        return 0
    finally:
        client.stop()


def _cmd_input(args: argparse.Namespace) -> int:
    client = _start_client(args.serial, max_fps=args.max_fps)
    try:
        if args.action == "tap":
            client.control.touch(args.x, args.y, scrcpy.ACTION_DOWN)
            client.control.touch(args.x, args.y, scrcpy.ACTION_UP)
        elif args.action == "swipe":
            client.control.swipe(args.x1, args.y1, args.x2, args.y2)
        elif args.action == "key":
            client.control.keycode(args.keycode)
        elif args.action == "text":
            client.control.text(args.text)
        else:
            raise RuntimeError(f"unsupported action: {args.action}")

        print(json.dumps({"action": args.action, "success": True}))
        return 0
    finally:
        client.stop()


def _cmd_probe(args: argparse.Namespace) -> int:
    run_dir = Path(args.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    client = _start_client(args.serial, max_fps=args.max_fps)
    captures: list[dict[str, object]] = []
    try:
        for index in range(args.captures):
            path = run_dir / f"capture_{index:02d}.png"
            size, width, height = _write_frame_png(client.last_frame, path)
            captures.append(
                {
                    "path": str(path),
                    "bytes": size,
                    "width": width,
                    "height": height,
                    "success": True,
                }
            )
            time.sleep(0.2)

        input_tap = True
        client.control.touch(10, 10, scrcpy.ACTION_DOWN)
        client.control.touch(10, 10, scrcpy.ACTION_UP)

        input_swipe = True
        client.control.swipe(100, 300, 100, 500)

        input_key = True
        client.control.keycode(scrcpy.KEYCODE_UNKNOWN)

        input_text = True
        client.control.text("")

        payload = {
            "connected": True,
            "captures": captures,
            "input_tap": input_tap,
            "input_swipe": input_swipe,
            "input_key": input_key,
            "input_text": input_text,
        }
        print(json.dumps(payload))
        return 0
    finally:
        client.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="py-scrcpy-client worker")
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect")
    connect.add_argument("--serial", required=True)
    connect.add_argument("--max-fps", type=int, default=5)

    capture = sub.add_parser("capture")
    capture.add_argument("--serial", required=True)
    capture.add_argument("--output", required=True)
    capture.add_argument("--max-fps", type=int, default=5)

    input_parser = sub.add_parser("input")
    input_parser.add_argument("--serial", required=True)
    input_parser.add_argument("--max-fps", type=int, default=5)
    input_sub = input_parser.add_subparsers(dest="action", required=True)

    tap = input_sub.add_parser("tap")
    tap.add_argument("x", type=int)
    tap.add_argument("y", type=int)

    swipe = input_sub.add_parser("swipe")
    swipe.add_argument("x1", type=int)
    swipe.add_argument("y1", type=int)
    swipe.add_argument("x2", type=int)
    swipe.add_argument("y2", type=int)

    key = input_sub.add_parser("key")
    key.add_argument("keycode", type=int)

    text = input_sub.add_parser("text")
    text.add_argument("text")

    probe = sub.add_parser("probe")
    probe.add_argument("--serial", required=True)
    probe.add_argument("--output-dir", required=True)
    probe.add_argument("--captures", type=int, default=3)
    probe.add_argument("--max-fps", type=int, default=5)

    args = parser.parse_args()
    if args.command == "connect":
        return _cmd_connect(args)
    if args.command == "capture":
        return _cmd_capture(args)
    if args.command == "input":
        return _cmd_input(args)
    if args.command == "probe":
        return _cmd_probe(args)
    raise RuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
