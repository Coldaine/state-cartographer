"""CLI surface for transport layer probe commands.

Thin argparse wrapper over state_cartographer.transport.

Usage:
    python scripts/memu_transport.py bootstrap
    python scripts/memu_transport.py doctor
    python scripts/memu_transport.py connect
    python scripts/memu_transport.py capture [--count N] [--output DIR]
    python scripts/memu_transport.py input tap X Y
    python scripts/memu_transport.py input swipe X1 Y1 X2 Y2 [--duration MS]
    python scripts/memu_transport.py input key KEYCODE
    python scripts/memu_transport.py input text TEXT
    python scripts/memu_transport.py probe maa [--captures N]
    python scripts/memu_transport.py probe scrcpy
    python scripts/memu_transport.py probe session
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure repo root is on path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from state_cartographer.transport.artifacts import probe_run_dir, write_json  # noqa: E402
from state_cartographer.transport.config import load_config  # noqa: E402
from state_cartographer.transport.discovery import bootstrap  # noqa: E402
from state_cartographer.transport.health import doctor  # noqa: E402
from state_cartographer.transport.maamcp import MaaAdapter, run_maa_probe  # noqa: E402
from state_cartographer.transport.models import (  # noqa: E402
    ObservationDecision,
    ProbeVerdict,
    ReadinessTier,
    SessionProbeReport,
)
from state_cartographer.transport.scrcpy_probe import run_scrcpy_probe  # noqa: E402


def _adb_path_from_manifest(cfg):
    """Get adb path from bootstrap or default."""
    manifest = bootstrap(cfg)
    for t in manifest.tools:
        if t.name == "adb" and t.found and t.path:
            return t.path
    return "adb"


def _apply_serial_override(args, cfg):
    """Apply --serial CLI override to config if provided."""
    if getattr(args, "serial", None):
        cfg.adb_serial = args.serial


def cmd_bootstrap(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    manifest = bootstrap(cfg)
    print(manifest.to_json())
    return 0 if manifest.all_required_found else 1


def cmd_doctor(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    adb_path = _adb_path_from_manifest(cfg)
    report = doctor(cfg, adb_path)
    print(report.to_json())
    return 0 if report.readiness_tier != ReadinessTier.UNREACHABLE else 1


def cmd_connect(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    adb_path = _adb_path_from_manifest(cfg)
    adapter = MaaAdapter(cfg.serial, adb_path, agent_path=cfg.agent_path)
    ok = adapter.connect()
    print(json.dumps({"connected": ok, "serial": cfg.serial, "backend": adapter.backend}))
    return 0 if ok else 1


def cmd_capture(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    adb_path = _adb_path_from_manifest(cfg)
    adapter = MaaAdapter(cfg.serial, adb_path, agent_path=cfg.agent_path)
    adapter.connect()

    out_dir = Path(args.output) if args.output else probe_run_dir("capture")
    count = args.count or 1
    results = []
    for i in range(count):
        path = out_dir / f"frame_{i:03d}.png"
        data, elapsed = adapter.screenshot(path)
        results.append({"path": str(path), "bytes": len(data), "elapsed_ms": round(elapsed, 1)})
        print(f"  [{i}] {path} ({len(data)} bytes, {elapsed:.0f}ms)")
    print(json.dumps(results, indent=2))
    return 0


def cmd_input(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    adb_path = _adb_path_from_manifest(cfg)
    adapter = MaaAdapter(cfg.serial, adb_path, agent_path=cfg.agent_path)
    adapter.connect()

    action = args.input_action
    if action == "tap":
        if len(args.params) != 2:
            print("tap requires X Y", file=sys.stderr)
            return 2
        ok = adapter.tap(int(args.params[0]), int(args.params[1]))
    elif action == "swipe":
        if len(args.params) != 4:
            print("swipe requires X1 Y1 X2 Y2", file=sys.stderr)
            return 2
        p = args.params
        duration = int(args.duration) if args.duration else 300
        ok = adapter.swipe(int(p[0]), int(p[1]), int(p[2]), int(p[3]), duration)
    elif action == "key":
        if len(args.params) != 1:
            print("key requires KEYCODE", file=sys.stderr)
            return 2
        ok = adapter.key(args.params[0])
    elif action == "text":
        if not args.params:
            print("text requires at least one TEXT token", file=sys.stderr)
            return 2
        ok = adapter.text(" ".join(args.params))
    else:
        print(f"Unknown input action: {action}", file=sys.stderr)
        return 1

    print(json.dumps({"action": action, "success": ok}))
    return 0 if ok else 1


def cmd_probe_maa(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    adb_path = _adb_path_from_manifest(cfg)
    report = run_maa_probe(cfg.serial, adb_path, agent_path=cfg.agent_path, capture_count=args.captures or 3)
    print(report.to_json())
    return 0 if report.verdict == ProbeVerdict.PASS else 1


def cmd_probe_scrcpy(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    report = run_scrcpy_probe(cfg.serial)
    print(report.to_json())
    return 0 if report.observation_decision in {ObservationDecision.RUNTIME_CONSUMABLE, ObservationDecision.DEBUG_ONLY} else 1


def cmd_probe_session(args):
    cfg = load_config(args.config)
    _apply_serial_override(args, cfg)
    adb_path = _adb_path_from_manifest(cfg)

    run_dir = probe_run_dir("session")
    session = SessionProbeReport(serial=cfg.serial, artifacts_dir=str(run_dir))

    # Bootstrap
    session.bootstrap = bootstrap(cfg)

    # Doctor
    doc = doctor(cfg, adb_path)
    session.doctor = doc
    session.degradation_codes.extend(doc.degradation_codes)

    if doc.readiness_tier == ReadinessTier.UNREACHABLE:
        # Hard gate: transport must be reachable
        session.verdict = ProbeVerdict.FAIL
        write_json(run_dir, "session-probe-report.json", session.to_json())
        print(session.to_json())
        return 1

    if doc.readiness_tier == ReadinessTier.DEGRADED:
        logging.warning("Doctor readiness=%s, continuing with degraded fallbacks", doc.readiness_tier)

    # MaaMCP probe
    maa = run_maa_probe(cfg.serial, adb_path, agent_path=cfg.agent_path, capture_count=args.captures or 3)
    session.maa = maa

    # scrcpy probe (with MaaMCP active)
    scrcpy = run_scrcpy_probe(cfg.serial, maa_active=maa.connected)
    session.scrcpy = scrcpy

    # Observation decision
    session.observation_decision = scrcpy.observation_decision
    if scrcpy.observation_decision == ObservationDecision.DEBUG_ONLY and "debug_only_visual" not in session.degradation_codes:
        session.degradation_codes.append("debug_only_visual")

    # Overall verdict
    if maa.verdict == ProbeVerdict.PASS:
        session.verdict = ProbeVerdict.PASS
    else:
        session.verdict = ProbeVerdict.FAIL

    write_json(run_dir, "session-probe-report.json", session.to_json())
    print(session.to_json())
    return 0 if session.verdict == ProbeVerdict.PASS else 1


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="MEmu transport layer CLI")
    parser.add_argument("--config", type=str, default=None, help="Path to transport config (default: configs/memu.json)")
    parser.add_argument("--serial", type=str, default=None, help="Override ADB serial from config")
    sub = parser.add_subparsers(dest="command", required=True)

    # bootstrap
    sub.add_parser("bootstrap", help="Discover and verify external tools")

    # doctor
    sub.add_parser("doctor", help="Run readiness checks")

    # connect
    sub.add_parser("connect", help="Connect to emulator and report status")

    # capture
    cap = sub.add_parser("capture", help="Capture screenshot(s)")
    cap.add_argument("--count", type=int, default=1, help="Number of captures")
    cap.add_argument("--output", type=str, default=None, help="Output directory")

    # input
    inp = sub.add_parser("input", help="Send input action")
    inp.add_argument("input_action", choices=["tap", "swipe", "key", "text"])
    inp.add_argument("params", nargs="*")
    inp.add_argument("--duration", type=int, default=None, help="Swipe duration in ms")

    # probe
    probe = sub.add_parser("probe", help="Run probe")
    probe_sub = probe.add_subparsers(dest="probe_type", required=True)

    maa_probe = probe_sub.add_parser("maa", help="MaaMCP acceptance probe")
    maa_probe.add_argument("--captures", type=int, default=3, help="Number of captures")

    probe_sub.add_parser("scrcpy", help="scrcpy coexistence probe")

    session_probe = probe_sub.add_parser("session", help="Full session probe")
    session_probe.add_argument("--captures", type=int, default=3, help="Number of captures")

    args = parser.parse_args()

    if args.command == "bootstrap":
        sys.exit(cmd_bootstrap(args))
    elif args.command == "doctor":
        sys.exit(cmd_doctor(args))
    elif args.command == "connect":
        sys.exit(cmd_connect(args))
    elif args.command == "capture":
        sys.exit(cmd_capture(args))
    elif args.command == "input":
        sys.exit(cmd_input(args))
    elif args.command == "probe":
        if args.probe_type == "maa":
            sys.exit(cmd_probe_maa(args))
        elif args.probe_type == "scrcpy":
            sys.exit(cmd_probe_scrcpy(args))
        elif args.probe_type == "session":
            sys.exit(cmd_probe_session(args))


if __name__ == "__main__":
    main()
