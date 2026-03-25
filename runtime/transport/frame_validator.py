from __future__ import annotations

from dataclasses import dataclass

from runtime.config.models import RuntimeConfig
from runtime.observation.frame_health import analyze_image
from runtime.observation.state_types import FrameEnvelope


@dataclass
class FrameValidator:
    config: RuntimeConfig
    previous_hash: str | None = None
    previous_seen_at: float | None = None

    def validate(self, path: str, *, source: str) -> FrameEnvelope:
        frame = analyze_image(
            path,
            previous_hash=self.previous_hash,
            previous_seen_at=self.previous_seen_at,
            black_threshold=self.config.black_frame_threshold,
            near_black_threshold=self.config.near_black_threshold,
            stale_timeout_s=self.config.stale_frame_timeout_s,
            source=source,
        )
        self.previous_hash = frame.frame_hash
        self.previous_seen_at = frame.captured_at_monotonic
        return frame
