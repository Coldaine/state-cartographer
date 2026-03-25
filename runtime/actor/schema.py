from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from runtime.controller.failure_codes import FailureCode


class ActionType(StrEnum):
    TAP = "tap"
    SWIPE = "swipe"
    KEY = "key"
    TEXT = "text"
    WAIT = "wait"


@dataclass(frozen=True)
class ActionCandidate:
    action_type: ActionType
    confidence: float
    uncertainty: float
    rationale: str
    target_point: tuple[float, float] | None = None
    bbox: tuple[float, float, float, float] | None = None
    swipe_to: tuple[float, float] | None = None
    keycode: str | None = None
    text: str | None = None


@dataclass(frozen=True)
class ActorDecision:
    screen_label: str | None
    transition_state: str
    candidates: tuple[ActionCandidate, ...]
    raw: dict[str, Any]
    failure_code: FailureCode | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    status: str
    confidence: float
    rationale: str
    observed_state: str | None = None
    failure_code: FailureCode | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _validate_float(value: Any, *, field_name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"invalid_{field_name}")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"invalid_{field_name}")
    return value


def parse_candidate(candidate: dict[str, Any]) -> ActionCandidate:
    action_type = ActionType(str(candidate["action_type"]).lower())
    confidence = _validate_float(candidate.get("confidence"), field_name="confidence")
    uncertainty = _validate_float(candidate.get("uncertainty"), field_name="uncertainty")
    rationale = str(candidate.get("rationale") or "").strip()
    if not rationale:
        raise ValueError("missing_rationale")

    target_point = None
    if candidate.get("target_point") is not None:
        point = candidate["target_point"]
        if not isinstance(point, dict):
            raise ValueError("invalid_target_point")
        target_point = (
            _validate_float(point.get("x"), field_name="target_x"),
            _validate_float(point.get("y"), field_name="target_y"),
        )

    bbox = None
    if candidate.get("bbox") is not None:
        bbox_values = candidate["bbox"]
        if not isinstance(bbox_values, list) or len(bbox_values) != 4:
            raise ValueError("invalid_bbox")
        bbox = tuple(_validate_float(value, field_name="bbox") for value in bbox_values)
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ValueError("invalid_bbox")

    swipe_to = None
    if candidate.get("swipe_to") is not None:
        swipe = candidate["swipe_to"]
        if not isinstance(swipe, dict):
            raise ValueError("invalid_swipe_to")
        swipe_to = (
            _validate_float(swipe.get("x"), field_name="swipe_x"),
            _validate_float(swipe.get("y"), field_name="swipe_y"),
        )

    if action_type in {ActionType.TAP, ActionType.SWIPE} and target_point is None:
        raise ValueError("missing_target_point")
    if action_type is ActionType.SWIPE and swipe_to is None:
        raise ValueError("missing_swipe_to")
    if action_type is ActionType.KEY and not str(candidate.get("keycode") or "").strip():
        raise ValueError("missing_keycode")
    if action_type is ActionType.TEXT and not str(candidate.get("text") or "").strip():
        raise ValueError("missing_text")

    return ActionCandidate(
        action_type=action_type,
        confidence=confidence,
        uncertainty=uncertainty,
        rationale=rationale,
        target_point=target_point,
        bbox=bbox,
        swipe_to=swipe_to,
        keycode=str(candidate.get("keycode") or "").strip() or None,
        text=str(candidate.get("text") or "").strip() or None,
    )


def parse_actor_decision(payload: dict[str, Any]) -> ActorDecision:
    candidates_payload = payload.get("candidates")
    if not isinstance(candidates_payload, list) or not candidates_payload:
        raise ValueError("missing_candidates")
    candidates = tuple(parse_candidate(item) for item in candidates_payload)
    transition_state = str(payload.get("transition_state") or "unknown_or_ambiguous_state")
    screen_label = str(payload.get("screen_label") or "").strip() or None
    notes = payload.get("notes") if isinstance(payload.get("notes"), list) else []
    return ActorDecision(
        screen_label=screen_label,
        transition_state=transition_state,
        candidates=candidates,
        raw=payload,
        notes=tuple(str(item) for item in notes),
    )
