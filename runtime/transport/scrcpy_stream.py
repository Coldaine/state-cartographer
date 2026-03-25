from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StreamStatus:
    primary_mode: str
    active_mode: str
    healthy: bool
    degraded: bool = False
    reason: str | None = None
    metrics: dict[str, object] = field(default_factory=dict)


class ScrcpyStream:
    """Primary stream substrate placeholder with explicit degraded-mode semantics.

    This first pass manages scrcpy process availability and exposes a health
    contract. Live decoded frames are left to a later integration slice when
    a stable scrcpy-capable client path is available in the target environment.
    """

    def __init__(self, serial: str, executable: str = "scrcpy", max_fps: int = 15):
        self.serial = serial
        self.executable = executable
        self.max_fps = max_fps
        self.process: subprocess.Popen[bytes] | None = None

    @property
    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def start(self) -> StreamStatus:
        if not self.available:
            return StreamStatus(
                primary_mode="scrcpy",
                active_mode="fallback",
                healthy=False,
                degraded=True,
                reason="scrcpy_binary_missing",
            )
        temp_record = Path(tempfile.gettempdir()) / "memu_scrcpy_probe.mp4"
        try:
            self.process = subprocess.Popen(
                [
                    self.executable,
                    "--serial",
                    self.serial,
                    "--no-audio",
                    "--no-window",
                    "--max-fps",
                    str(self.max_fps),
                    "--record",
                    str(temp_record),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return StreamStatus(
                primary_mode="scrcpy",
                active_mode="scrcpy",
                healthy=True,
                metrics={"probe_record_path": str(temp_record)},
            )
        except Exception as exc:
            return StreamStatus(
                primary_mode="scrcpy",
                active_mode="fallback",
                healthy=False,
                degraded=True,
                reason=f"scrcpy_start_failed:{exc}",
            )

    def stop(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process = None
