from __future__ import annotations

import unittest

from runtime.controller.failure_codes import FailureCode
from runtime.controller.retry_policy import RetryPolicy


class RetryPolicyTests(unittest.TestCase):
    def test_transition_failure_retries(self) -> None:
        policy = RetryPolicy(max_retries=2)
        self.assertTrue(policy.should_retry(FailureCode.TRANSITION_IN_PROGRESS, 1))
        self.assertFalse(policy.should_retry(FailureCode.TRANSITION_IN_PROGRESS, 2))


if __name__ == "__main__":
    unittest.main()
