"""Resource model — tracks game/system state beyond screen navigation.

[!] STATUS: MVP PLACEHOLDER PROTOTYPE
This file is currently a structural placeholder. It provides a data model
to hold state (oil, coins, timers), but completely lacks the automated OCR
and dynamic screen-reading capabilities required to actually populate these
values from the screen during live gameplay.

Resources are observable values (oil, coins, timers, dock capacity, etc.)that inform scheduling and task decisions. They are updated by observation
(reading from screenshots or API calls), not hardcoded arithmetic.

The resource store persists as part of the session file.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def create_store() -> dict[str, Any]:
    """Create a new empty resource store."""
    return {
        "resources": {},
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }


def get_resource(store: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Get a resource entry by name, or None if not tracked."""
    return store.get("resources", {}).get(name)


def get_value(store: dict[str, Any], name: str) -> Any:
    """Get just the value of a resource, or None if not tracked."""
    entry = get_resource(store, name)
    return entry["value"] if entry else None


def set_resource(
    store: dict[str, Any],
    name: str,
    value: Any,
    *,
    source: str = "observation",
) -> dict[str, Any]:
    """Set a resource value with timestamp and source tracking.

    Args:
        store: The resource store to update
        name: Resource name (e.g. "oil", "coins", "dock_capacity")
        value: The observed value
        source: How this value was obtained ("observation", "ocr", "estimate")

    Returns:
        The updated store.
    """
    now = datetime.now(tz=UTC).isoformat()
    if "resources" not in store:
        store["resources"] = {}

    store["resources"][name] = {
        "value": value,
        "updated_at": now,
        "source": source,
    }
    store["updated_at"] = now
    return store


def check_threshold(
    store: dict[str, Any],
    name: str,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
) -> bool:
    """Check if a resource is within acceptable thresholds.

    Returns True if the resource meets all specified constraints.
    Returns True if the resource is not tracked (unknown = permissive).
    """
    entry = get_resource(store, name)
    if entry is None:
        return True  # Unknown resources don't block

    value = entry["value"]
    if not isinstance(value, (int, float)):
        return True  # Non-numeric resources can't be threshold-checked

    if min_value is not None and value < min_value:
        return False
    return not (max_value is not None and value > max_value)


def list_resources(store: dict[str, Any]) -> list[str]:
    """Return the names of all tracked resources."""
    return list(store.get("resources", {}).keys())


def set_timer(
    store: dict[str, Any],
    name: str,
    expires_at: datetime,
    *,
    source: str = "observation",
) -> dict[str, Any]:
    """Set a timer resource (expires_at is an ISO datetime string).

    Timers are resources whose value is an expiry timestamp.
    """
    return set_resource(store, name, expires_at.isoformat(), source=source)


def is_timer_expired(store: dict[str, Any], name: str) -> bool | None:
    """Check if a timer resource has expired.

    Returns True if expired, False if still running, None if not tracked.
    """
    entry = get_resource(store, name)
    if entry is None:
        return None

    value = entry["value"]
    if not isinstance(value, str):
        return None

    try:
        expires = datetime.fromisoformat(value)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(tz=UTC) >= expires
    except ValueError:
        return None


def save_store(store: dict[str, Any], path: Path) -> None:
    """Persist the resource store to a JSON file."""
    with open(path, "w") as f:
        json.dump(store, f, indent=2, default=str)
        f.write("\n")


def load_store(path: Path) -> dict[str, Any]:
    """Load a resource store from a JSON file."""
    with open(path) as f:
        return json.load(f)
