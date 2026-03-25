from __future__ import annotations

import json

from runtime.observation.context_contract import CompactContext


def build_actor_system_prompt() -> str:
    return (
        "You are a local Android UI actor for a Unity game running in an emulator. "
        "You must propose bounded actions from the current frame and compact context only. "
        "Do not invent hidden state. Return strict JSON."
    )


def build_actor_user_prompt(context: CompactContext) -> str:
    return f"""Analyze the current frame and propose up to 3 bounded next actions.

Context:
{json.dumps(context.to_payload(), sort_keys=True)}

Return JSON with:
- screen_label: short screen/state label
- transition_state: one of ["stable_state", "transition_state", "obstructed_or_modal_state", "unknown_or_ambiguous_state"]
- notes: array of short strings
- candidates: array of 1-3 items, each with:
  - action_type: one of ["tap", "swipe", "key", "text", "wait"]
  - confidence: float 0.0-1.0
  - uncertainty: float 0.0-1.0
  - rationale: short string grounded in visible evidence
  - target_point: {{"x":0.0-1.0,"y":0.0-1.0}} or null
  - bbox: [x1,y1,x2,y2] normalized 0.0-1.0 or null
  - swipe_to: {{"x":0.0-1.0,"y":0.0-1.0}} or null
  - keycode: string or null
  - text: string or null

Rules:
- prefer visible grounded actions
- if the screen appears mid-transition, include a top candidate of action_type "wait"
- if uncertain, raise uncertainty rather than guessing
- for tap and swipe actions, target_point is required
- for swipe actions, swipe_to is required
- do not exceed 3 candidates
"""


def build_verifier_system_prompt() -> str:
    return (
        "You are a post-action verifier for Android UI automation. "
        "Judge only from the before/after frames and compact context. Return strict JSON."
    )


def build_verifier_user_prompt(context: CompactContext, executed_action: str) -> str:
    return f"""You are given two images in order:
1. before action
2. after action

Compact context:
{json.dumps(context.to_payload(), sort_keys=True)}

Executed action:
{executed_action}

Return JSON with:
- status: one of ["changed_as_expected", "changed_but_uncertain", "no_change", "transition_in_progress", "stream_invalid"]
- confidence: float 0.0-1.0
- observed_state: short label or null
- rationale: short string grounded in visible evidence
"""
