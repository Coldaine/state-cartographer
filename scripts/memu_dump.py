"""memu_dump.py - Dump MEmu emulator instance settings via memuc CLI.

Reads rendering mode, resolution, DPI, CPU, memory, FPS, and root status
for a given MEmu instance. Outputs human-readable summary or JSON.

Usage:
    python scripts/memu_dump.py                    # defaults to MEmu_1 (index 1)
    python scripts/memu_dump.py --index 0          # dump MEmu_0
    python scripts/memu_dump.py --json             # machine-readable output
    python scripts/memu_dump.py --memuc /path/to/memuc.exe
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Keys to query and how to present them
CONFIG_KEYS: list[tuple[str, str]] = [
    ("graphics_render_mode", "Rendering"),
    ("resolution_width", "Width"),
    ("resolution_height", "Height"),
    ("vbox_dpi", "DPI"),
    ("cpus", "CPUs"),
    ("memory", "Memory (MB)"),
    ("fps", "FPS"),
    ("enable_su", "Root"),
]

RENDER_MODES = {"0": "OpenGL", "1": "DirectX"}
BOOL_FIELDS = {"enable_su": {"0": False, "1": True}}


def find_memuc(override: str | None = None) -> Path:
    """Resolve memuc.exe path.

    Resolution order:
    1. Explicit override (--memuc flag)
    2. Derive from ALAS config (alas.json -> EmulatorInfo.path)
    3. Common install paths as last resort
    """
    if override:
        p = Path(override)
        if p.is_file():
            return p
        raise FileNotFoundError(f"memuc.exe not found at override path: {override}")

    # Try ALAS config
    alas_config = Path(__file__).parent.parent / "vendor" / "AzurLaneAutoScript" / "config" / "alas.json"
    if alas_config.is_file():
        with open(alas_config) as f:
            cfg = json.load(f)
        emu_path = cfg.get("Alas", {}).get("EmulatorInfo", {}).get("path", "")
        if emu_path:
            memuc = Path(emu_path).parent / "memuc.exe"
            if memuc.is_file():
                return memuc

    # Common install paths
    for guess in [
        Path("D:/Program Files/Microvirt/MEmu/memuc.exe"),
        Path("C:/Program Files/Microvirt/MEmu/memuc.exe"),
        Path("C:/Program Files (x86)/Microvirt/MEmu/memuc.exe"),
    ]:
        if guess.is_file():
            return guess

    raise FileNotFoundError(
        "memuc.exe not found. Use --memuc to specify the path, or ensure ALAS config has a valid EmulatorInfo.path."
    )


def run_memuc(memuc: Path, args: list[str], timeout: float = 5) -> str:
    """Run a memuc command and return stdout.

    Uses Popen + kill on Windows to handle memuc's tendency to hang
    (especially `listvms` when the management console isn't responsive).
    """
    cmd = [str(memuc), *args]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait(timeout=3)
        raise RuntimeError(f"memuc {' '.join(args)} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"memuc {' '.join(args)} failed (rc={proc.returncode}): {stderr.strip() or stdout.strip()}")
    return stdout.strip()


def list_vms(memuc: Path) -> list[dict[str, str]]:
    """Parse memuc listvms output into structured rows.

    Example output line: "0,MEmu,Running,0,0"
    Fields: index, name, status, pid(?), unknown
    """
    raw = run_memuc(memuc, ["listvms"])
    vms = []
    for line in raw.splitlines():
        parts = line.split(",")
        if len(parts) >= 3:
            vms.append(
                {
                    "index": parts[0].strip(),
                    "name": parts[1].strip(),
                    "status": parts[2].strip(),
                }
            )
    return vms


def get_config(memuc: Path, index: int, key: str) -> str:
    """Read a single config value for a VM instance.

    memuc getconfig returns lines like "Value: 0" — strip the prefix.
    """
    raw = run_memuc(memuc, ["getconfig", "-i", str(index), key])
    if raw.startswith("Value: "):
        return raw[7:]
    return raw


def dump_instance(memuc: Path, index: int) -> dict[str, Any]:
    """Dump all interesting config keys for a given instance."""
    result: dict[str, Any] = {"index": index}

    # Get instance name from listvms
    try:
        vms = list_vms(memuc)
        for vm in vms:
            if vm["index"] == str(index):
                result["name"] = vm["name"]
                result["status"] = vm["status"]
                break
    except RuntimeError:
        pass  # listvms may fail if management service isn't running

    # Query each config key
    raw_values: dict[str, str] = {}
    for key, _label in CONFIG_KEYS:
        try:
            raw_values[key] = get_config(memuc, index, key)
        except RuntimeError as e:
            raw_values[key] = f"ERROR: {e}"

    # Build structured output
    render_raw = raw_values.get("graphics_render_mode", "")
    result["rendering"] = RENDER_MODES.get(render_raw, f"unknown ({render_raw})")

    width = raw_values.get("resolution_width", "?")
    height = raw_values.get("resolution_height", "?")
    result["resolution"] = {"width": _int_or_raw(width), "height": _int_or_raw(height)}

    result["dpi"] = _int_or_raw(raw_values.get("vbox_dpi", "?"))
    result["cpus"] = _int_or_raw(raw_values.get("cpus", "?"))
    result["memory_mb"] = _int_or_raw(raw_values.get("memory", "?"))
    result["fps"] = _int_or_raw(raw_values.get("fps", "?"))

    su_raw = raw_values.get("enable_su", "")
    result["root_enabled"] = BOOL_FIELDS["enable_su"].get(su_raw, su_raw)

    return result


def _int_or_raw(value: str) -> int | str:
    """Convert to int if possible, otherwise return raw string."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


def format_human(data: dict[str, Any]) -> str:
    """Format dump result as human-readable text."""
    lines = []
    lines.append(f"MEmu Instance: {data.get('name', '?')} (index {data['index']})")
    if "status" in data:
        lines.append(f"  Status:     {data['status']}")
    lines.append(f"  Rendering:  {data['rendering']}")
    res = data.get("resolution", {})
    lines.append(f"  Resolution: {res.get('width', '?')}x{res.get('height', '?')}")
    lines.append(f"  DPI:        {data.get('dpi', '?')}")
    lines.append(f"  CPUs:       {data.get('cpus', '?')}")
    lines.append(f"  Memory:     {data.get('memory_mb', '?')} MB")
    lines.append(f"  FPS:        {data.get('fps', '?')}")
    lines.append(f"  Root:       {data.get('root_enabled', '?')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dump MEmu emulator instance settings")
    parser.add_argument(
        "--index",
        type=int,
        default=1,
        help="MEmu instance index (default: 1 for MEmu_1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON instead of human-readable text",
    )
    parser.add_argument(
        "--memuc",
        type=str,
        default=None,
        help="Explicit path to memuc.exe",
    )
    args = parser.parse_args(argv)

    try:
        memuc = find_memuc(args.memuc)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        data = dump_instance(memuc, args.index)
    except Exception as e:
        print(f"Error dumping instance {args.index}: {e}", file=sys.stderr)
        return 1

    if args.json_output:
        print(json.dumps(data, indent=2))
    else:
        print(format_human(data))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
