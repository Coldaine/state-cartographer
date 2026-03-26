"""Transport config loading and validation.

Tracked config (configs/memu.json) owns:
  - pinned serial
  - primary control tool choice
  - preferred visual tool
  - fallback observation decision

Machine-specific paths, ports, versions, and probe state go in ignored
artifacts under data/events/memu-transport/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Repo root is two levels up from this file
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "configs" / "memu.json"


@dataclass
class TransportConfig:
    """Validated transport configuration from tracked config."""

    name: str = "MEmu Player"
    emulator_type: str = "memu"
    adb_serial: str = "127.0.0.1:21513"
    primary_control: str = "maatouch"
    primary_observation: str = "adb_screencap"
    agent_path: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def serial(self) -> str:
        return self.adb_serial

    @property
    def host(self) -> str:
        return self.adb_serial.split(":")[0]

    @property
    def port(self) -> int:
        parts = self.adb_serial.split(":")
        return int(parts[1]) if len(parts) > 1 else 5555


def load_config(path: Path | str | None = None) -> TransportConfig:
    """Load transport config from tracked JSON.

    Falls back to repo default at configs/memu.json.
    """
    p = Path(path) if path else _DEFAULT_CONFIG
    if not p.exists():
        raise FileNotFoundError(f"Transport config not found: {p}")

    with open(p, encoding="utf-8") as f:
        raw = json.load(f)

    return TransportConfig(
        name=raw.get("name", "MEmu Player"),
        emulator_type=raw.get("emulator_type", "memu"),
        adb_serial=raw.get("adb_serial", "127.0.0.1:21513"),
        primary_control=raw.get("primary_control", "maatouch"),
        primary_observation=raw.get("primary_observation", "adb_screencap"),
        agent_path=raw.get("agent_path", None),
        raw=raw,
    )


def repo_root() -> Path:
    return _REPO_ROOT


def artifacts_dir() -> Path:
    d = _REPO_ROOT / "data" / "events" / "memu-transport"
    d.mkdir(parents=True, exist_ok=True)
    return d
