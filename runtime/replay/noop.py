from __future__ import annotations

from runtime.replay.interface import ReplayResult


class NoopReplay:
    def lookup(self, frame_path: str, objective_context: str) -> ReplayResult:
        return ReplayResult(status="miss")

    def insert(self, pre_state: str, action: dict[str, object], post_state: str, objective_context: str) -> None:
        return None

    def invalidate(self, entry_id: str, reason: str) -> None:
        return None

    def eligible(self, entry: dict[str, object]) -> bool:
        return False
