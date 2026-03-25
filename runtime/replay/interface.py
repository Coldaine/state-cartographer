from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReplayResult:
    status: str
    hint_status: str = "none"
    search_mode: str = "global"
    entry_id: str | None = None
    confidence: float | None = None
    action_hint: dict[str, object] | None = None


class ReplayLayer(Protocol):
    def lookup(self, frame_path: str, objective_context: str) -> ReplayResult: ...

    def insert(self, pre_state: str, action: dict[str, object], post_state: str, objective_context: str) -> None: ...

    def invalidate(self, entry_id: str, reason: str) -> None: ...

    def eligible(self, entry: dict[str, object]) -> bool: ...
