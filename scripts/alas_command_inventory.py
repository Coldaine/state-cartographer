"""Extract the ALAS command surface into a repo-owned JSON inventory.

This script inventories two related surfaces from the vendor checkout:

1. Scheduler-visible commands defined in the shipped ALAS configs
2. Public runtime methods on ``AzurLaneAutoScript`` in ``alas.py``

The scheduler-visible inventory is the assignment layer that ALAS can be
configured to run. The direct-only inventory surfaces callable runtime methods
that exist in code but are not exposed as standard scheduler commands.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIGS = [
    REPO_ROOT / "vendor/AzurLaneAutoScript/config/template.json",
    REPO_ROOT / "vendor/AzurLaneAutoScript/config/alas.json",
    REPO_ROOT / "vendor/AzurLaneAutoScript/config/PatrickCustom.json",
]
DEFAULT_ALAS_PY = REPO_ROOT / "vendor/AzurLaneAutoScript/alas.py"

INTERNAL_METHODS = {
    "__init__",
    "run",
    "save_error_log",
    "wait_until",
    "get_next_task",
    "loop",
}


def camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def categorize_command(command: str) -> str:
    if command in {"Restart"}:
        return "lifecycle"
    if command in {
        "Main",
        "Main2",
        "Main3",
        "GemsFarming",
        "Event",
        "Event2",
        "EventA",
        "EventB",
        "EventC",
        "EventD",
        "EventSp",
        "Raid",
        "RaidDaily",
        "Hospital",
        "Coalition",
        "CoalitionSp",
        "MaritimeEscort",
        "WarArchives",
    }:
        return "campaign_event"
    if command.startswith("Opsi"):
        return "operation_siren"
    if command in {
        "Commission",
        "Tactical",
        "Research",
        "Dorm",
        "Meowfficer",
        "Guild",
        "Reward",
        "Awaken",
        "Daily",
        "Hard",
        "Exercise",
        "ShopFrequent",
        "ShopOnce",
        "Shipyard",
        "Gacha",
        "Freebies",
        "Minigame",
        "PrivateQuarters",
    }:
        return "maintenance"
    return "other"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_scheduler_occurrences(node: Any, path: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(node, dict):
        scheduler = node.get("Scheduler")
        if isinstance(scheduler, dict):
            command = scheduler.get("Command")
            if isinstance(command, str) and command:
                out.append(
                    {
                        "task_path": ".".join(path),
                        "command": command,
                        "command_path": ".".join(path + ["Scheduler", "Command"]),
                    }
                )
        for key, value in node.items():
            out.extend(_iter_scheduler_occurrences(value, path + [str(key)]))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out.extend(_iter_scheduler_occurrences(value, path + [str(index)]))
    return out


def extract_scheduler_commands(config_paths: list[Path]) -> dict[str, dict[str, Any]]:
    commands: dict[str, dict[str, Any]] = {}

    for path in config_paths:
        data = load_json(path)
        for occurrence in _iter_scheduler_occurrences(data, []):
            command = occurrence["command"]
            entry = commands.setdefault(
                command,
                {
                    "command": command,
                    "method": camel_to_snake(command),
                    "category": categorize_command(command),
                    "config_sections": set(),
                    "config_files": set(),
                    "occurrences": [],
                },
            )
            top_level = occurrence["task_path"].split(".", 1)[0] if occurrence["task_path"] else ""
            entry["config_sections"].add(top_level)
            entry["config_files"].add(path.name)
            entry["occurrences"].append(
                {
                    "config_file": path.name,
                    "task_path": occurrence["task_path"],
                    "command_path": occurrence["command_path"],
                }
            )

    normalized: dict[str, dict[str, Any]] = {}
    for command, entry in commands.items():
        normalized[command] = {
            "command": entry["command"],
            "method": entry["method"],
            "category": entry["category"],
            "config_sections": sorted(entry["config_sections"]),
            "config_files": sorted(entry["config_files"]),
            "occurrences": sorted(
                entry["occurrences"],
                key=lambda item: (item["config_file"], item["task_path"], item["command_path"]),
            ),
        }
    return normalized


def extract_public_methods(alas_py: Path) -> dict[str, dict[str, Any]]:
    tree = ast.parse(alas_py.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AzurLaneAutoScript":
            methods: dict[str, dict[str, Any]] = {}
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                name = item.name
                if name.startswith("_") or name in INTERNAL_METHODS:
                    continue
                methods[name] = {"method": name, "line": item.lineno}
            return dict(sorted(methods.items()))
    raise RuntimeError(f"AzurLaneAutoScript class not found in {alas_py}")


def build_inventory(config_paths: list[Path], alas_py: Path) -> dict[str, Any]:
    scheduled = extract_scheduler_commands(config_paths)
    public_methods = extract_public_methods(alas_py)
    scheduled_methods = {entry["method"] for entry in scheduled.values()}

    scheduled_commands = []
    for key in sorted(scheduled):
        entry = dict(scheduled[key])
        method = public_methods.get(entry["method"])
        entry["method_exists"] = method is not None
        entry["method_line"] = method["line"] if method else None
        entry["dispatchable"] = method is not None
        scheduled_commands.append(entry)

    direct_only = [
        {
            "method": method,
            "category": "direct_only",
            "line": meta["line"],
        }
        for method, meta in public_methods.items()
        if method not in scheduled_methods
    ]

    return {
        "source": {
            "configs": [str(path) for path in config_paths],
            "alas_py": str(alas_py),
        },
        "scheduled_commands": scheduled_commands,
        "direct_only_methods": direct_only,
        "summary": {
            "scheduled_count": len(scheduled),
            "direct_only_count": len(direct_only),
            "public_method_count": len(public_methods),
            "scheduled_occurrence_count": sum(len(entry["occurrences"]) for entry in scheduled.values()),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory ALAS commands/tasks")
    parser.add_argument(
        "--config",
        dest="configs",
        action="append",
        help="Path to an ALAS config JSON. May be passed multiple times.",
    )
    parser.add_argument(
        "--alas-py",
        default=str(DEFAULT_ALAS_PY),
        help=f"Path to alas.py (default: {DEFAULT_ALAS_PY})",
    )
    parser.add_argument("--output", help="Write JSON inventory to this file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_paths = [Path(p) for p in args.configs] if args.configs else DEFAULT_CONFIGS
    alas_py = Path(args.alas_py)

    inventory = build_inventory(config_paths=config_paths, alas_py=alas_py)
    rendered = json.dumps(inventory, indent=2 if args.pretty or args.output else None)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        sys.stdout.write(rendered + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
