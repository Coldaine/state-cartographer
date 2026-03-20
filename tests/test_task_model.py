"""Tests for task_model.py — task loading, validation, and serialization."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from task_model import (
    get_next_run,
    get_task,
    is_task_enabled,
    load_tasks,
    set_next_run,
    validate_task_manifest,
)

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# --- Fixtures ---


@pytest.fixture
def minimal_manifest():
    return {
        "tasks": {
            "commission": {
                "entry_state": "page_commission",
                "schedule": {"type": "interval", "interval_minutes": 60},
                "actions": [
                    {"type": "navigate", "target_state": "page_commission"},
                    {"type": "tap", "coords": [640, 400]},
                ],
            }
        }
    }


@pytest.fixture
def full_manifest():
    return {
        "meta": {"version": "1.0.0"},
        "tasks": {
            "reward": {
                "entry_state": "page_reward",
                "enabled": True,
                "schedule": {"type": "interval", "interval_minutes": 20},
                "actions": [{"type": "tap", "coords": [100, 200]}],
                "next_run": "2020-01-01T00:00:00",
            },
            "commission": {
                "entry_state": "page_commission",
                "enabled": True,
                "schedule": {"type": "interval", "interval_minutes": 60},
                "actions": [],
                "next_run": "2026-12-01T00:00:00",
            },
            "disabled_task": {
                "entry_state": "page_main",
                "enabled": False,
                "schedule": {"type": "manual"},
                "actions": [],
            },
        },
    }


# --- Validation ---


class TestValidateManifest:
    def test_valid_minimal(self, minimal_manifest):
        errors = validate_task_manifest(minimal_manifest)
        assert errors == []

    def test_missing_tasks_key(self):
        errors = validate_task_manifest({})
        assert any("Missing required key" in e for e in errors)

    def test_tasks_not_dict(self):
        errors = validate_task_manifest({"tasks": []})
        assert any("must be a dict" in e for e in errors)

    def test_missing_entry_state(self):
        manifest = {
            "tasks": {
                "bad": {"schedule": {"type": "manual"}},
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("entry_state" in e for e in errors)

    def test_missing_schedule(self):
        manifest = {
            "tasks": {
                "bad": {"entry_state": "page_main"},
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("schedule" in e for e in errors)

    def test_invalid_schedule_type(self):
        manifest = {
            "tasks": {
                "bad": {
                    "entry_state": "page_main",
                    "schedule": {"type": "bogus"},
                },
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("bogus" in e for e in errors)

    def test_interval_missing_minutes(self):
        manifest = {
            "tasks": {
                "bad": {
                    "entry_state": "page_main",
                    "schedule": {"type": "interval"},
                },
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("interval_minutes" in e for e in errors)

    def test_invalid_action_type(self):
        manifest = {
            "tasks": {
                "bad": {
                    "entry_state": "page_main",
                    "schedule": {"type": "manual"},
                    "actions": [{"type": "explode"}],
                },
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("explode" in e for e in errors)

    def test_navigate_missing_target(self):
        manifest = {
            "tasks": {
                "bad": {
                    "entry_state": "page_main",
                    "schedule": {"type": "manual"},
                    "actions": [{"type": "navigate"}],
                },
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("target_state" in e for e in errors)

    def test_tap_missing_coords(self):
        manifest = {
            "tasks": {
                "bad": {
                    "entry_state": "page_main",
                    "schedule": {"type": "manual"},
                    "actions": [{"type": "tap"}],
                },
            }
        }
        errors = validate_task_manifest(manifest)
        assert any("coords" in e for e in errors)


# --- Task accessors ---


class TestGetTask:
    def test_existing_task(self, full_manifest):
        task = get_task(full_manifest, "reward")
        assert task is not None
        assert task["entry_state"] == "page_reward"

    def test_missing_task(self, full_manifest):
        assert get_task(full_manifest, "nonexistent") is None


class TestIsTaskEnabled:
    def test_enabled_explicit(self, full_manifest):
        task = get_task(full_manifest, "reward")
        assert is_task_enabled(task)

    def test_disabled(self, full_manifest):
        task = get_task(full_manifest, "disabled_task")
        assert not is_task_enabled(task)

    def test_default_enabled(self, minimal_manifest):
        task = get_task(minimal_manifest, "commission")
        assert is_task_enabled(task)


class TestNextRun:
    def test_parse_iso_string(self, full_manifest):
        task = get_task(full_manifest, "reward")
        nr = get_next_run(task)
        assert nr is not None
        assert nr.year == 2020

    def test_none_when_not_set(self, minimal_manifest):
        task = get_task(minimal_manifest, "commission")
        assert get_next_run(task) is None

    def test_set_next_run(self, minimal_manifest):
        task = get_task(minimal_manifest, "commission")
        future = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
        set_next_run(task, future)
        assert get_next_run(task) == future


# --- Load from disk ---


class TestLoadFromDisk:
    def test_load_azur_lane_tasks(self):
        path = EXAMPLES_DIR / "azur-lane" / "tasks.json"
        if not path.exists():
            pytest.skip("Azur Lane tasks.json not found")
        manifest = load_tasks(path)
        assert "tasks" in manifest
        assert len(manifest["tasks"]) >= 5

    def test_load_validates(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"tasks": "not_a_dict"}))
        with pytest.raises(ValueError):
            load_tasks(bad_file)
