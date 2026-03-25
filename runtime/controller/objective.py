from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeObjective:
    tag: str
    instruction: str
    max_steps: int = 1
