from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    adb_serial: str
    objective_tag: str = "commission_collect"
    scrcpy_executable: str = "scrcpy"
    scrcpy_max_fps: int = 15
    stream_fallback: str = "droidcast"
    droidcast_url: str | None = None
    artifact_root: Path = Path("data/runtime")
    actor_base_url: str = "http://localhost:18900/v1"
    actor_model: str = "local-vlm"
    verifier_model: str | None = None
    settle_delay_ms: int = 500
    verification_window_ms: int = 1200
    repeated_frame_threshold: int = 3
    black_frame_threshold: float = 2.0
    near_black_threshold: float = 8.0
    stale_frame_timeout_s: float = 2.0
    extras: dict[str, object] = field(default_factory=dict)
