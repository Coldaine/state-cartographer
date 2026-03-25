from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from runtime.controller.failure_codes import FailureCode


class TransitionState(StrEnum):
    STABLE = "stable_state"
    TRANSITION = "transition_state"
    OBSTRUCTED = "obstructed_or_modal_state"
    UNKNOWN = "unknown_or_ambiguous_state"


@dataclass(frozen=True)
class FrameHealth:
    mean_luma: float
    variance: float
    entropy: float
    is_black: bool
    is_near_black: bool
    is_repeated: bool
    is_stale: bool
    is_disconnected: bool = False
    failures: tuple[FailureCode, ...] = ()


@dataclass(frozen=True)
class FrameEnvelope:
    path: Path
    width: int
    height: int
    source: str
    captured_at_monotonic: float
    frame_hash: str
    health: FrameHealth
    transition_state: TransitionState = TransitionState.UNKNOWN
    labels: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
