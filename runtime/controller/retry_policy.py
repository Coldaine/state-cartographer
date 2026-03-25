from __future__ import annotations

from dataclasses import dataclass

from runtime.controller.failure_codes import FailureCode


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2

    def should_retry(self, failure_code: FailureCode | None, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        return failure_code in {
            FailureCode.TRANSITION_IN_PROGRESS,
            FailureCode.STREAM_NEAR_BLACK_FRAME,
            FailureCode.STREAM_STALE_FRAME,
            FailureCode.LOCAL_ACTOR_LOW_CONFIDENCE,
            FailureCode.LOCAL_ACTOR_CANDIDATE_AMBIGUOUS,
        }
