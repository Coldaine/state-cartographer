from __future__ import annotations

from dataclasses import dataclass

from runtime.actor.schema import ActionCandidate, ActionType
from runtime.transport.input_controller import InputController


@dataclass(frozen=True)
class ExecutedAction:
    action_type: str
    detail: dict[str, object]


class ActionExecutor:
    def __init__(self, input_controller: InputController):
        self.input = input_controller

    def execute(self, candidate: ActionCandidate) -> ExecutedAction:
        if candidate.action_type is ActionType.TAP and candidate.target_point is not None:
            px, py = self.input.tap(*candidate.target_point)
            return ExecutedAction(action_type="tap", detail={"pixel": [px, py]})
        if candidate.action_type is ActionType.SWIPE and candidate.target_point and candidate.swipe_to:
            pixels = self.input.swipe(*candidate.target_point, *candidate.swipe_to)
            return ExecutedAction(action_type="swipe", detail={"pixels": list(pixels)})
        if candidate.action_type is ActionType.KEY and candidate.keycode:
            self.input.key(candidate.keycode)
            return ExecutedAction(action_type="key", detail={"keycode": candidate.keycode})
        if candidate.action_type is ActionType.TEXT and candidate.text:
            self.input.text(candidate.text)
            return ExecutedAction(action_type="text", detail={"text": candidate.text})
        return ExecutedAction(action_type="wait", detail={})
