from __future__ import annotations

from runtime.observation.state_types import FrameEnvelope, TransitionState


class TransitionTracker:
    def classify(
        self, before_frame: FrameEnvelope, after_frame: FrameEnvelope, verification_status: str | None
    ) -> TransitionState:
        if verification_status == "transition_in_progress":
            return TransitionState.TRANSITION
        if before_frame.frame_hash == after_frame.frame_hash:
            return TransitionState.STABLE
        if after_frame.health.is_near_black or after_frame.health.is_black:
            return TransitionState.OBSTRUCTED
        return TransitionState.STABLE
