"""Tests for alas_action_inventory.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from alas_action_inventory import build_inventory, parse_class_methods  # noqa: E402


def test_parse_class_methods_reads_real_control_surface():
    methods = parse_class_methods(
        REPO_ROOT / "vendor" / "AzurLaneAutoScript" / "module" / "device" / "control.py",
        "Control",
    )
    assert "click" in methods
    assert "swipe" in methods
    assert "drag" in methods


def test_build_inventory_contains_core_primitive_and_semantic_actions():
    inventory = build_inventory()

    primitive = {entry["name"] for entry in inventory["primitive_actions"]}
    semantic = {entry["name"] for entry in inventory["semantic_actions"]}

    assert "click" in primitive
    assert "app_start" in primitive
    assert "screenshot" in primitive

    assert "ui_goto" in semantic
    assert "ui_goto_main" in semantic
    assert "handle_popup_confirm" in semantic
    assert "handle_story_skip" in semantic

    assert inventory["metadata"]["primitive_action_count"] >= 10
    assert inventory["metadata"]["semantic_action_count"] >= 20


def test_cli_writes_inventory_json(tmp_path: Path):
    output = tmp_path / "action-inventory.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "alas_action_inventory.py"),
            "--pretty",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["metadata"]["primitive_action_count"] >= 10
    assert data["metadata"]["semantic_action_count"] >= 20
    assert any(target["class_name"] == "Control" for target in data["instrumentation_targets"])
