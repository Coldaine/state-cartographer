from __future__ import annotations

import time
from dataclasses import dataclass

from runtime.actor.candidate_ranker import rank_candidates, score_candidate
from runtime.actor.router import LocalActorRouter
from runtime.actor.verifier import PostActionVerifier
from runtime.config.models import RuntimeConfig
from runtime.controller.action_executor import ActionExecutor
from runtime.controller.failure_codes import FailureCode
from runtime.controller.objective import RuntimeObjective
from runtime.controller.retry_policy import RetryPolicy
from runtime.controller.transition_tracker import TransitionTracker
from runtime.logging.artifacts import ArtifactLogger
from runtime.observation.context_contract import CompactContext
from runtime.observation.frame_sampler import FrameSampler
from runtime.observation.state_types import TransitionState
from runtime.replay.interface import ReplayLayer
from runtime.teacher.interface import TeacherLayer


@dataclass(frozen=True)
class LoopStep:
    index: int
    frame_path: str
    source: str
    failure_code: str | None
    selected_action: str | None
    verification_status: str | None
    transition_state: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoopRunResult:
    status: str
    steps: tuple[LoopStep, ...]
    run_dir: str
    last_failure_code: str | None = None


class RuntimeLoop:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        sampler: FrameSampler,
        actor: LocalActorRouter,
        verifier: PostActionVerifier,
        executor: ActionExecutor,
        retry_policy: RetryPolicy,
        replay: ReplayLayer,
        teacher: TeacherLayer,
        artifacts: ArtifactLogger,
    ):
        self.config = config
        self.sampler = sampler
        self.actor = actor
        self.verifier = verifier
        self.executor = executor
        self.retry_policy = retry_policy
        self.replay = replay
        self.teacher = teacher
        self.artifacts = artifacts
        self.transition_tracker = TransitionTracker()

    def run(self, objective: RuntimeObjective) -> LoopRunResult:
        steps: list[LoopStep] = []
        context = CompactContext(objective_tag=objective.tag)

        stream_status = self.sampler.start_stream()
        self.artifacts.log_event("stream_status", stream_status.__dict__)

        for index in range(1, objective.max_steps + 1):
            step_dir = self.artifacts.step_dir(index)
            frame = self.sampler.sample(step_dir, name="before")
            failure_code = frame.health.failures[0] if frame.health.failures else None
            if failure_code in {
                FailureCode.STREAM_BLACK_FRAME,
                FailureCode.STREAM_NEAR_BLACK_FRAME,
                FailureCode.STREAM_STALE_FRAME,
                FailureCode.STREAM_REPEATED_FRAME,
            } and not self.retry_policy.should_retry(failure_code, context.retry_count):
                step = LoopStep(
                    index=index,
                    frame_path=str(frame.path),
                    source=frame.source,
                    failure_code=failure_code.value,
                    selected_action=None,
                    verification_status=None,
                    transition_state=TransitionState.UNKNOWN.value,
                    notes=("frame_unhealthy",),
                )
                steps.append(step)
                self.artifacts.log_event("step", step.__dict__)
                return LoopRunResult("stream_unhealthy", tuple(steps), str(self.artifacts.run_dir), failure_code.value)

            replay_result = self.replay.lookup(str(frame.path), objective.tag)
            context = CompactContext(
                objective_tag=objective.tag,
                last_screen_label=context.last_screen_label,
                last_actions=context.last_actions,
                last_action_outcome=context.last_action_outcome,
                retry_count=context.retry_count,
                replay_hint=replay_result.action_hint,
                transition_state=frame.transition_state,
            )

            decision = self.actor.propose(frame.path, context)
            if decision.failure_code is not None or not decision.candidates:
                failure_code = (decision.failure_code or FailureCode.LOCAL_ACTOR_CANDIDATE_AMBIGUOUS).value
                step = LoopStep(
                    index=index,
                    frame_path=str(frame.path),
                    source=frame.source,
                    failure_code=failure_code,
                    selected_action=None,
                    verification_status=None,
                    transition_state=decision.transition_state,
                    notes=decision.notes,
                )
                steps.append(step)
                self.artifacts.log_event("step", {**step.__dict__, "decision": decision.raw})
                return LoopRunResult("actor_failed", tuple(steps), str(self.artifacts.run_dir), failure_code)

            ranked = rank_candidates(decision)
            candidate = ranked[0]
            if score_candidate(candidate) < 0.35:
                step = LoopStep(
                    index=index,
                    frame_path=str(frame.path),
                    source=frame.source,
                    failure_code=FailureCode.LOCAL_ACTOR_LOW_CONFIDENCE.value,
                    selected_action=None,
                    verification_status=None,
                    transition_state=decision.transition_state,
                    notes=("top_candidate_below_threshold",),
                )
                steps.append(step)
                self.artifacts.log_event("step", {**step.__dict__, "decision": decision.raw})
                return LoopRunResult(
                    "actor_rejected",
                    tuple(steps),
                    str(self.artifacts.run_dir),
                    FailureCode.LOCAL_ACTOR_LOW_CONFIDENCE.value,
                )

            executed = self.executor.execute(candidate)
            time.sleep(self.config.settle_delay_ms / 1000)
            after_frame = self.sampler.sample(step_dir, name="after")
            verification = self.verifier.verify(frame.path, after_frame.path, context, executed.action_type)
            transition_state = self.transition_tracker.classify(frame, after_frame, verification.status)

            step = LoopStep(
                index=index,
                frame_path=str(frame.path),
                source=frame.source,
                failure_code=verification.failure_code.value if verification.failure_code else None,
                selected_action=executed.action_type,
                verification_status=verification.status,
                transition_state=transition_state.value,
                notes=(candidate.rationale,),
            )
            steps.append(step)
            self.artifacts.log_event(
                "step",
                {
                    **step.__dict__,
                    "decision": decision.raw,
                    "candidate": candidate.__dict__,
                    "executed": executed.__dict__,
                    "verification": verification.raw,
                },
            )

            context = CompactContext(
                objective_tag=objective.tag,
                last_screen_label=verification.observed_state or decision.screen_label,
                last_actions=(*(context.last_actions[-2:]), executed.action_type),
                last_action_outcome=verification.status,
                retry_count=0,
                replay_hint=None,
                transition_state=transition_state,
            )

            if verification.status == "changed_as_expected":
                continue
            if verification.status == "changed_but_uncertain":
                return LoopRunResult("changed_but_uncertain", tuple(steps), str(self.artifacts.run_dir))
            if verification.status in {"no_change", "stream_invalid"}:
                return LoopRunResult(
                    "verification_failed",
                    tuple(steps),
                    str(self.artifacts.run_dir),
                    verification.failure_code.value if verification.failure_code else None,
                )

        return LoopRunResult("step_budget_exhausted", tuple(steps), str(self.artifacts.run_dir))
