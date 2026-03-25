from __future__ import annotations

import argparse
import json

from runtime.actor.router import LocalActorRouter
from runtime.actor.verifier import PostActionVerifier
from runtime.config.loader import load_runtime_config
from runtime.controller.action_executor import ActionExecutor
from runtime.controller.loop import RuntimeLoop
from runtime.controller.objective import RuntimeObjective
from runtime.controller.retry_policy import RetryPolicy
from runtime.logging.artifacts import ArtifactLogger
from runtime.observation.frame_sampler import FrameSampler
from runtime.replay.noop import NoopReplay
from runtime.teacher.noop import NoopTeacher
from runtime.transport.frame_validator import FrameValidator
from runtime.transport.memu_instance import MEmuInstance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stream-first MEmu runtime scaffold.")
    parser.add_argument("--config", default="configs/memu.json")
    parser.add_argument("--objective", required=True, help="Natural-language objective instruction.")
    parser.add_argument("--objective-tag", default=None, help="Compact objective tag override.")
    parser.add_argument("--max-steps", type=int, default=1, help="Bounded action budget for this run.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_runtime_config(args.config)
    objective = RuntimeObjective(
        tag=args.objective_tag or config.objective_tag,
        instruction=args.objective,
        max_steps=max(1, args.max_steps),
    )
    instance = MEmuInstance(config)
    artifacts = ArtifactLogger(config.artifact_root)
    sampler = FrameSampler(config, instance.adb, instance.stream, FrameValidator(config))
    actor = LocalActorRouter(config.actor_base_url, config.actor_model)
    verifier = PostActionVerifier(config.actor_base_url, config.verifier_model or config.actor_model)
    loop = RuntimeLoop(
        config=config,
        sampler=sampler,
        actor=actor,
        verifier=verifier,
        executor=ActionExecutor(instance.input_controller()),
        retry_policy=RetryPolicy(),
        replay=NoopReplay(),
        teacher=NoopTeacher(),
        artifacts=artifacts,
    )
    result = loop.run(objective)
    print(
        json.dumps(
            {"status": result.status, "run_dir": result.run_dir, "steps": [step.__dict__ for step in result.steps]},
            indent=2,
        )
    )
    return 0 if result.status in {"step_budget_exhausted", "changed_but_uncertain"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
