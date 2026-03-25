from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TeacherResponse:
    status: str
    notes: tuple[str, ...] = ()
    recommended_actions: tuple[dict[str, object], ...] = ()


class TeacherLayer(Protocol):
    def escalate(self, payload: dict[str, object]) -> TeacherResponse: ...
