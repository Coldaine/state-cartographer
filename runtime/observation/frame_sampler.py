from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from runtime.config.models import RuntimeConfig
from runtime.observation.state_types import FrameEnvelope
from runtime.transport.adb_client import ADBClient
from runtime.transport.frame_validator import FrameValidator
from runtime.transport.scrcpy_stream import ScrcpyStream, StreamStatus


@dataclass
class FrameSampler:
    config: RuntimeConfig
    adb: ADBClient
    stream: ScrcpyStream
    validator: FrameValidator

    def start_stream(self) -> StreamStatus:
        return self.stream.start()

    def sample(self, output_dir: str | Path, *, name: str) -> FrameEnvelope:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        image_path = target_dir / f"{name}.png"

        if self.stream.available and self.stream.process is not None:
            return self._sample_fallback(image_path, source="fallback_via_live_stream_session")
        return self._sample_fallback(image_path, source=f"fallback_{self.config.stream_fallback}")

    def _sample_fallback(self, image_path: Path, *, source: str) -> FrameEnvelope:
        if self.config.stream_fallback == "adb":
            image_path.write_bytes(self.adb.exec_out("screencap", "-p"))
            return self.validator.validate(str(image_path), source=source)

        if not self.config.droidcast_url:
            raise RuntimeError("fallback_capture_unavailable:no_droidcast_url")
        response = requests.get(f"{self.config.droidcast_url.rstrip('/')}/screenshot", timeout=10)
        response.raise_for_status()
        image_path.write_bytes(response.content)
        return self.validator.validate(str(image_path), source=source)

    def sample_temp(self, *, name: str) -> FrameEnvelope:
        return self.sample(Path(tempfile.mkdtemp(prefix="runtime-frame-")), name=name)
