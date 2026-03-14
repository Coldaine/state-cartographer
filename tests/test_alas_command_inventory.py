# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.alas_command_inventory import build_inventory

CONFIGS = [
    REPO_ROOT / "vendor/AzurLaneAutoScript/config/template.json",
    REPO_ROOT / "vendor/AzurLaneAutoScript/config/alas.json",
    REPO_ROOT / "vendor/AzurLaneAutoScript/config/PatrickCustom.json",
]
ALAS_PY = REPO_ROOT / "vendor/AzurLaneAutoScript/alas.py"


def _scheduled_map(inventory: dict) -> dict[str, dict]:
    return {entry["command"]: entry for entry in inventory["scheduled_commands"]}


def test_build_inventory_finds_expected_scheduler_surface():
    inventory = build_inventory(config_paths=CONFIGS, alas_py=ALAS_PY)
    scheduled = _scheduled_map(inventory)

    assert inventory["summary"]["scheduled_count"] == 51
    assert inventory["summary"]["scheduled_occurrence_count"] == 153
    assert "Restart" in scheduled
    assert "Commission" in scheduled
    assert "EventSp" in scheduled
    assert "OpsiExplore" in scheduled

    assert scheduled["Restart"]["method"] == "restart"
    assert scheduled["Restart"]["method_exists"] is True
    assert scheduled["OpsiAshBeacon"]["method"] == "opsi_ash_beacon"
    assert scheduled["Commission"]["category"] == "maintenance"
    assert scheduled["Event"]["category"] == "campaign_event"
    assert scheduled["OpsiExplore"]["category"] == "operation_siren"
    assert len(scheduled["Commission"]["occurrences"]) == 3


def test_build_inventory_exposes_direct_only_runtime_methods():
    inventory = build_inventory(config_paths=CONFIGS, alas_py=ALAS_PY)
    direct_only = {entry["method"] for entry in inventory["direct_only_methods"]}

    assert "start" in direct_only
    assert "goto_main" in direct_only
    assert "daemon" in direct_only
    assert "opsi_daemon" in direct_only


def test_build_inventory_records_scheduler_occurrence_paths():
    inventory = build_inventory(config_paths=CONFIGS, alas_py=ALAS_PY)
    scheduled = _scheduled_map(inventory)
    occurrence = scheduled["Restart"]["occurrences"][0]

    assert occurrence["config_file"] in {
        "template.json",
        "alas.json",
        "PatrickCustom.json",
    }
    assert occurrence["task_path"] == "Restart"
    assert occurrence["command_path"] == "Restart.Scheduler.Command"
