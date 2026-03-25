from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


class ArtifactLogger:
    def __init__(self, root: str | Path):
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = Path(root) / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.run_dir / "events.jsonl"

    def step_dir(self, index: int) -> Path:
        target = self.run_dir / f"step-{index:03d}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": event_type, **_normalize(payload)}, sort_keys=True) + "\n")
