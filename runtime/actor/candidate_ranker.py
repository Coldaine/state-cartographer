from __future__ import annotations

from runtime.actor.schema import ActionCandidate, ActorDecision


def score_candidate(candidate: ActionCandidate) -> float:
    return candidate.confidence - (candidate.uncertainty * 0.6)


def rank_candidates(decision: ActorDecision) -> tuple[ActionCandidate, ...]:
    return tuple(sorted(decision.candidates, key=score_candidate, reverse=True))
