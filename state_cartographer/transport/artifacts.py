"""Artifact persistence for transport probes.

All artifacts go under data/events/memu-transport/ (gitignored).
Each probe run gets a timestamped subdirectory.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from state_cartographer.transport.config import artifacts_dir


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def probe_run_dir(label: str = "probe") -> Path:
    d = artifacts_dir() / f"{_ts()}_{label}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(directory: Path, name: str, data: dict[str, Any] | str) -> Path:
    p = directory / name
    content = data if isinstance(data, str) else json.dumps(data, indent=2)
    p.write_text(content, encoding="utf-8")
    return p


def write_bytes(directory: Path, name: str, data: bytes) -> Path:
    p = directory / name
    p.write_bytes(data)
    return p
