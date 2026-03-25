from __future__ import annotations

from enum import StrEnum


class FailureCode(StrEnum):
    STREAM_BLACK_FRAME = "stream_black_frame"
    STREAM_NEAR_BLACK_FRAME = "stream_near_black_frame"
    STREAM_STALE_FRAME = "stream_stale_frame"
    STREAM_REPEATED_FRAME = "stream_repeated_frame"
    STREAM_DISCONNECTED = "stream_disconnected"
    REPLAY_EMPTY = "replay_empty"
    REPLAY_SIMILARITY_BELOW_THRESHOLD = "replay_similarity_below_threshold"
    REPLAY_POST_ACTION_MISMATCH = "replay_post_action_mismatch"
    REPLAY_COLLISION_SUSPECTED = "replay_collision_suspected"
    LOCAL_ACTOR_LOW_CONFIDENCE = "local_actor_low_confidence"
    LOCAL_ACTOR_CANDIDATE_AMBIGUOUS = "local_actor_candidate_ambiguous"
    LOCAL_ACTOR_BOUNDARY_VIOLATION = "local_actor_boundary_violation"
    POST_ACTION_NO_STATE_CHANGE = "post_action_no_state_change"
    TRANSITION_IN_PROGRESS = "transition_in_progress"
    OVERLAY_OBSTRUCTION = "overlay_obstruction"
    UNKNOWN_SCREEN = "unknown_screen"
    RECOVERY_LOOP_DETECTED = "recovery_loop_detected"
    STREAM_INVALID = "stream_invalid"
