"""emulator_config.py - Load emulator configurations from JSON files.

Usage:
    from scripts.emulator_config import load_config, get_config_path

    config = load_config("ldplayer")  # or "memu"
    print(config["adb_serial"])  # 127.0.0.1:5555
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "configs"


def get_config_path(name: str) -> Path:
    """Return the path to a config file by name.

    Args:
        name: Config name (e.g., "memu", "ldplayer")

    Returns:
        Path to the JSON config file
    """
    return DEFAULT_CONFIG_DIR / f"{name}.json"


def load_config(name: str) -> dict[str, Any]:
    """Load an emulator configuration from JSON.

    Args:
        name: Config name (e.g., "memu", "ldplayer")

    Returns:
        Dict with emulator configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    config_path = get_config_path(name)

    if not config_path.exists():
        available = [p.stem for p in DEFAULT_CONFIG_DIR.glob("*.json")]
        raise FileNotFoundError(f"Config '{name}' not found at {config_path}. Available configs: {available}")

    with open(config_path) as f:
        return json.load(f)


def list_configs() -> list[str]:
    """List all available emulator configurations.

    Returns:
        List of config names (without .json extension)
    """
    return [p.stem for p in DEFAULT_CONFIG_DIR.glob("*.json")]


def get_serial(name: str) -> str:
    """Get the ADB serial for a given config name."""
    return load_config(name)["adb_serial"]


def main() -> int:
    """CLI to list and show configs."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Emulator config utility")
    parser.add_argument("--list", action="store_true", help="List available configs")
    parser.add_argument("--show", metavar="NAME", help="Show a specific config")

    args = parser.parse_args()

    if args.list:
        configs = list_configs()
        print(f"Available configs in {DEFAULT_CONFIG_DIR}:")
        for name in configs:
            print(f"  - {name}")
        return 0

    if args.show:
        try:
            config = load_config(args.show)
            print(json.dumps(config, indent=2))
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
