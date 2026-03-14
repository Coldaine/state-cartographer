"""Extract ALAS action surfaces and instrumentation hook points.

This inventory separates:

- primitive emulator/device actions
- higher-level semantic UI actions composed from them
- exact files/classes that should be instrumented for execution logging
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALAS_ROOT = REPO_ROOT / "vendor" / "AzurLaneAutoScript"

CONTROL_PY = ALAS_ROOT / "module" / "device" / "control.py"
APP_CONTROL_PY = ALAS_ROOT / "module" / "device" / "app_control.py"
SCREENSHOT_PY = ALAS_ROOT / "module" / "device" / "screenshot.py"
DEVICE_PY = ALAS_ROOT / "module" / "device" / "device.py"
BASE_PY = ALAS_ROOT / "module" / "base" / "base.py"
UI_PY = ALAS_ROOT / "module" / "ui" / "ui.py"
LOGIN_PY = ALAS_ROOT / "module" / "handler" / "login.py"
INFO_HANDLER_PY = ALAS_ROOT / "module" / "handler" / "info_handler.py"
FAST_FORWARD_PY = ALAS_ROOT / "module" / "handler" / "fast_forward.py"

PRIMITIVE_TARGETS: list[tuple[Path, str, list[str]]] = [
    (CONTROL_PY, "Control", ["click", "multi_click", "long_click", "swipe", "swipe_vector", "drag"]),
    (APP_CONTROL_PY, "AppControl", ["app_current", "app_is_running", "app_start", "app_stop", "dump_hierarchy"]),
    (
        SCREENSHOT_PY,
        "Screenshot",
        ["screenshot", "save_screenshot", "screenshot_interval_set", "image_save", "image_show"],
    ),
    (DEVICE_PY, "Device", ["screenshot", "dump_hierarchy", "get_orientation"]),
]

SEMANTIC_TARGETS: list[tuple[Path, str, list[str]]] = [
    (
        BASE_PY,
        "ModuleBase",
        [
            "appear_then_click",
            "wait_until_appear",
            "wait_until_appear_then_click",
            "wait_until_disappear",
            "wait_until_stable",
        ],
    ),
    (
        UI_PY,
        "UI",
        [
            "ui_page_appear",
            "ui_main_appear_then_click",
            "ensure_button_execute",
            "ui_click",
            "ui_goto",
            "ui_goto_main",
            "ui_goto_campaign",
            "ui_goto_event",
            "ui_goto_sp",
            "ui_back",
            "handle_idle_page",
        ],
    ),
    (
        LOGIN_PY,
        "LoginHandler",
        [
            "app_stop",
            "app_start",
            "app_restart",
            "handle_cn_user_agreement",
            "handle_app_login",
            "handle_user_agreement",
            "handle_user_login",
            "ensure_no_unfinished_campaign",
        ],
    ),
    (
        INFO_HANDLER_PY,
        "InfoHandler",
        [
            "handle_popup_confirm",
            "handle_popup_cancel",
            "handle_popup_single",
            "handle_popup_single_white",
            "handle_urgent_commission",
            "handle_guild_popup_confirm",
            "handle_guild_popup_cancel",
            "handle_mission_popup_go",
            "handle_mission_popup_ack",
            "handle_story_skip",
            "ensure_no_story",
            "handle_game_tips",
        ],
    ),
    (
        FAST_FORWARD_PY,
        "FastForwardHandler",
        [
            "handle_fast_forward",
            "handle_map_fleet_lock",
            "handle_auto_search",
            "handle_auto_search_setting",
            "handle_auto_submarine_call_disable",
            "handle_auto_search_continue",
            "handle_map_stop",
            "handle_2x_book_setting",
            "handle_2x_book_popup",
            "handle_map_walk_speedup",
        ],
    ),
]


@dataclass(frozen=True)
class MethodRecord:
    name: str
    class_name: str
    lineno: int
    file_path: Path


def parse_class_methods(path: Path, class_name: str) -> dict[str, MethodRecord]:
    """Return methods defined on one class, keyed by method name."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                item.name: MethodRecord(
                    name=item.name,
                    class_name=class_name,
                    lineno=item.lineno,
                    file_path=path,
                )
                for item in node.body
                if isinstance(item, ast.FunctionDef)
            }
    raise ValueError(f"Class {class_name!r} not found in {path}")


def _category_for_semantic(record: MethodRecord) -> str:
    module_name = record.file_path.name
    name = record.name
    if module_name == "ui.py":
        return "navigation"
    if module_name == "base.py":
        return "matching_waiting"
    if module_name == "login.py":
        return "login_recovery"
    if module_name == "info_handler.py":
        return "popup_reward"
    if module_name == "fast_forward.py":
        return "combat_support"
    if name.startswith("handle_"):
        return "handler"
    return "other"


def _serialize(record: MethodRecord, *, layer: str, category: str) -> dict[str, object]:
    return {
        "name": record.name,
        "class_name": record.class_name,
        "file": str(record.file_path),
        "line": record.lineno,
        "layer": layer,
        "category": category,
    }


def build_inventory() -> dict[str, object]:
    primitive_actions: list[dict[str, object]] = []
    semantic_actions: list[dict[str, object]] = []

    instrumentation_targets: list[dict[str, str]] = []
    for path, class_name, method_names in PRIMITIVE_TARGETS:
        methods = parse_class_methods(path, class_name)
        instrumentation_targets.append(
            {
                "file": str(path),
                "class_name": class_name,
                "reason": "primitive emulator/device actions",
            }
        )
        for method_name in method_names:
            record = methods[method_name]
            primitive_actions.append(_serialize(record, layer="primitive", category="device"))

    for path, class_name, method_names in SEMANTIC_TARGETS:
        methods = parse_class_methods(path, class_name)
        instrumentation_targets.append(
            {
                "file": str(path),
                "class_name": class_name,
                "reason": "semantic UI action orchestration",
            }
        )
        for method_name in method_names:
            record = methods[method_name]
            semantic_actions.append(
                _serialize(record, layer="semantic", category=_category_for_semantic(record))
            )

    primitive_actions.sort(key=lambda row: (row["file"], row["line"], row["name"]))
    semantic_actions.sort(key=lambda row: (row["file"], row["line"], row["name"]))

    return {
        "metadata": {
            "primitive_action_count": len(primitive_actions),
            "semantic_action_count": len(semantic_actions),
        },
        "primitive_actions": primitive_actions,
        "semantic_actions": semantic_actions,
        "instrumentation_targets": instrumentation_targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ALAS action surface inventory as JSON")
    parser.add_argument("--output", type=Path, help="Write JSON to file instead of stdout")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    try:
        inventory = build_inventory()
    except (OSError, ValueError, SyntaxError) as exc:
        sys.stderr.write(f"Failed to build action inventory: {exc}\n")
        return 1

    text = json.dumps(inventory, indent=2 if args.pretty else None, sort_keys=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
