"""Tests for resource_model.py — resource tracking, thresholds, timers."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from resource_model import (
    check_threshold,
    create_store,
    get_resource,
    get_value,
    is_timer_expired,
    list_resources,
    load_store,
    save_store,
    set_resource,
    set_timer,
)


class TestCreateStore:
    def test_creates_empty_store(self):
        store = create_store()
        assert store["resources"] == {}
        assert "updated_at" in store

    def test_has_timestamp(self):
        store = create_store()
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(store["updated_at"])
        assert dt.year >= 2026


class TestSetGetResource:
    def test_set_and_get(self):
        store = create_store()
        set_resource(store, "oil", 5000)
        entry = get_resource(store, "oil")
        assert entry is not None
        assert entry["value"] == 5000
        assert entry["source"] == "observation"

    def test_get_value_shortcut(self):
        store = create_store()
        set_resource(store, "coins", 12345)
        assert get_value(store, "coins") == 12345

    def test_get_missing_resource(self):
        store = create_store()
        assert get_resource(store, "gems") is None
        assert get_value(store, "gems") is None

    def test_custom_source(self):
        store = create_store()
        set_resource(store, "oil", 3000, source="ocr")
        entry = get_resource(store, "oil")
        assert entry["source"] == "ocr"

    def test_updates_timestamp(self):
        store = create_store()
        old_ts = store["updated_at"]
        set_resource(store, "oil", 100)
        assert store["updated_at"] >= old_ts

    def test_overwrite_resource(self):
        store = create_store()
        set_resource(store, "oil", 1000)
        set_resource(store, "oil", 2000)
        assert get_value(store, "oil") == 2000


class TestListResources:
    def test_empty(self):
        store = create_store()
        assert list_resources(store) == []

    def test_multiple(self):
        store = create_store()
        set_resource(store, "oil", 100)
        set_resource(store, "coins", 200)
        names = list_resources(store)
        assert set(names) == {"oil", "coins"}


class TestCheckThreshold:
    def test_above_min(self):
        store = create_store()
        set_resource(store, "oil", 500)
        assert check_threshold(store, "oil", min_value=100)

    def test_below_min(self):
        store = create_store()
        set_resource(store, "oil", 50)
        assert not check_threshold(store, "oil", min_value=100)

    def test_below_max(self):
        store = create_store()
        set_resource(store, "dock_pct", 85)
        assert check_threshold(store, "dock_pct", max_value=90)

    def test_above_max(self):
        store = create_store()
        set_resource(store, "dock_pct", 95)
        assert not check_threshold(store, "dock_pct", max_value=90)

    def test_unknown_resource_passes(self):
        store = create_store()
        assert check_threshold(store, "nonexistent", min_value=100)

    def test_non_numeric_passes(self):
        store = create_store()
        set_resource(store, "status", "active")
        assert check_threshold(store, "status", min_value=100)

    def test_both_min_and_max(self):
        store = create_store()
        set_resource(store, "oil", 500)
        assert check_threshold(store, "oil", min_value=100, max_value=1000)
        assert not check_threshold(store, "oil", min_value=600, max_value=1000)


class TestTimers:
    def test_set_timer(self):
        store = create_store()
        future = datetime.now(tz=UTC) + timedelta(hours=2)
        set_timer(store, "commission_1", future)
        entry = get_resource(store, "commission_1")
        assert entry is not None
        assert "T" in entry["value"]  # ISO format

    def test_unexpired_timer(self):
        store = create_store()
        future = datetime.now(tz=UTC) + timedelta(hours=2)
        set_timer(store, "research", future)
        assert is_timer_expired(store, "research") is False

    def test_expired_timer(self):
        store = create_store()
        past = datetime.now(tz=UTC) - timedelta(hours=1)
        set_timer(store, "dorm_food", past)
        assert is_timer_expired(store, "dorm_food") is True

    def test_unknown_timer(self):
        store = create_store()
        assert is_timer_expired(store, "nonexistent") is None


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        store = create_store()
        set_resource(store, "oil", 5000)
        set_resource(store, "coins", 12000)

        path = tmp_path / "resources.json"
        save_store(store, path)

        loaded = load_store(path)
        assert get_value(loaded, "oil") == 5000
        assert get_value(loaded, "coins") == 12000
