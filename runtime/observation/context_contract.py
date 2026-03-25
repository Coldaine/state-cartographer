from __future__ import annotations

from dataclasses import asdict, dataclass, field

from runtime.observation.state_types import TransitionState


@dataclass(frozen=True)
class CompactContext:
    objective_tag: str
    last_screen_label: str | None = None
    last_actions: tuple[str, ...] = ()
    last_action_outcome: str | None = None
    retry_count: int = 0
    replay_hint: dict[str, object] | None = None
    transition_state: TransitionState = TransitionState.UNKNOWN

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["transition_state"] = self.transition_state.value
        return payload


@dataclass(frozen=True)
class ObservationWindow:
    current: CompactContext
    previous_frames: tuple[str, ...] = field(default_factory=tuple)
